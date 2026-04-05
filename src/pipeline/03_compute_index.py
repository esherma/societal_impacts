"""
Step 3: Compute the county-level AI exposure index via Bartik shift-share.

Formula:
  AI_Exposure(county) = Σ_k [ share_k(county) × exposure_score_k ]

Where:
  share_k(county) = employment in occ category k / total employment in county
  exposure_score_k = employment-weighted avg observed_exposure for SOC codes
                     that fall within category k

Output: data/processed/county_exposure.parquet (and .csv)
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
PROC_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

# SOC prefix → ACS occupation category crosswalk
# This is the inverse of what we stored in the tidy file — we'll parse soc_prefixes.
# exposure_score for each ACS category = mean(observed_exposure) across all 6-digit
# SOC occupations whose code starts with any prefix in the category's prefix list.


def load_exposure() -> pd.DataFrame:
    """Load Anthropic job_exposure.csv with SOC codes and observed_exposure."""
    path = RAW_DIR / "labor_market_impacts" / "job_exposure.csv"
    df = pd.read_csv(path)
    # occ_code looks like "11-1011" — normalize to "11-1011" format
    df["occ_code"] = df["occ_code"].astype(str).str.strip()
    return df[["occ_code", "title", "observed_exposure"]]


def compute_category_scores(exposure_df: pd.DataFrame, tidy_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each ACS occupation category, compute the weighted-average exposure score
    across the SOC codes that fall in that category.

    We use a simple average here (all SOC occupations in the group weighted equally).
    A more precise approach would weight by national employment, but for Phase 1
    this is a reasonable first pass — and the SOC detail within each ACS group
    is similar in exposure level anyway.
    """
    # Get unique (occ_category, soc_prefixes) pairs
    cat_prefixes = (
        tidy_df[["occ_category", "soc_prefixes"]]
        .drop_duplicates()
        .set_index("occ_category")["soc_prefixes"]
    )

    rows = []
    for category, prefix_str in cat_prefixes.items():
        prefixes = prefix_str.split("|")

        # Find all SOC occupations matching any prefix
        mask = pd.Series(False, index=exposure_df.index)
        for prefix in prefixes:
            mask |= exposure_df["occ_code"].str.startswith(prefix)

        matched = exposure_df[mask]
        if matched.empty:
            score = np.nan
            n_occ = 0
        else:
            score = matched["observed_exposure"].mean()
            n_occ = len(matched)

        rows.append({
            "occ_category": category,
            "soc_prefixes": prefix_str,
            "category_exposure": score,
            "n_occupations_matched": n_occ,
            "matched_titles": "; ".join(matched["title"].head(5).tolist()),
        })

    return pd.DataFrame(rows)


def compute_county_exposure(tidy_df: pd.DataFrame, cat_scores: pd.DataFrame) -> pd.DataFrame:
    """
    Bartik shift-share:
      exposure(county) = Σ_k share_k(county) × score_k

    Returns one row per county with:
      fips, county_name, observed_exposure, total_employment, top_3_categories
    """
    # Join category scores into tidy data
    tidy = tidy_df.merge(cat_scores[["occ_category", "category_exposure"]], on="occ_category", how="left")

    # For each county, compute total employment
    county_totals = tidy.groupby("fips")["employment"].sum().rename("total_employment")
    tidy = tidy.join(county_totals, on="fips")

    # Share of each occupation in county
    tidy["share"] = tidy["employment"] / tidy["total_employment"].replace(0, np.nan)

    # Weighted contribution
    tidy["weighted_exposure"] = tidy["share"] * tidy["category_exposure"]

    # Sum to county level
    county_exposure = (
        tidy.groupby(["fips", "county_name"])
        .agg(
            observed_exposure=("weighted_exposure", "sum"),
            total_employment=("total_employment", "first"),
        )
        .reset_index()
    )

    # Compute top contributing categories per county
    def top_categories(group):
        top = (
            group.nlargest(3, "weighted_exposure")[["occ_category", "weighted_exposure"]]
            .apply(lambda r: f"{r['occ_category']} ({r['weighted_exposure']:.3f})", axis=1)
            .tolist()
        )
        return "; ".join(top)

    top_cats = tidy.groupby("fips").apply(top_categories, include_groups=False).rename("top_3_categories")
    county_exposure = county_exposure.join(top_cats, on="fips")

    # Extract state FIPS and county FIPS
    county_exposure["state_fips"] = county_exposure["fips"].str[:2]
    county_exposure["county_fips"] = county_exposure["fips"].str[2:]

    # Clean up county name (remove ", State" suffix for display)
    county_exposure["county_name_short"] = county_exposure["county_name"].str.split(",").str[0]
    county_exposure["state_name"] = county_exposure["county_name"].str.split(", ").str[-1]

    return county_exposure.sort_values("observed_exposure", ascending=False)


def main():
    print("Loading Anthropic exposure data...")
    exposure_df = load_exposure()
    print(f"  {len(exposure_df)} occupations, exposure range: "
          f"{exposure_df['observed_exposure'].min():.3f} – {exposure_df['observed_exposure'].max():.3f}")

    print("Loading ACS tidy occupation data...")
    tidy_df = pd.read_parquet(RAW_DIR / "acs_county_occupations_tidy.parquet")
    print(f"  {tidy_df['fips'].nunique()} counties, {tidy_df['occ_category'].nunique()} categories")

    print("Computing ACS category → exposure score crosswalk...")
    cat_scores = compute_category_scores(exposure_df, tidy_df)
    print("\nCategory exposure scores:")
    for _, row in cat_scores.sort_values("category_exposure", ascending=False).iterrows():
        print(f"  {row['occ_category']:<55s}  {row['category_exposure']:.4f}  "
              f"(n={row['n_occupations_matched']})")

    # Check for unmatched categories
    missing = cat_scores[cat_scores["category_exposure"].isna()]
    if not missing.empty:
        print(f"\nWARNING: {len(missing)} categories had no matching SOC occupations:")
        print(missing[["occ_category", "soc_prefixes"]].to_string(index=False))

    # Save crosswalk
    crosswalk_path = PROC_DIR / "occ_category_crosswalk.csv"
    cat_scores.drop(columns=["matched_titles"]).to_csv(crosswalk_path, index=False)
    print(f"\nCrosswalk saved to {crosswalk_path}")

    print("\nComputing county-level shift-share exposure index...")
    county_df = compute_county_exposure(tidy_df, cat_scores)
    print(f"  Counties computed: {len(county_df)}")
    print(f"  Exposure range: {county_df['observed_exposure'].min():.4f} – "
          f"{county_df['observed_exposure'].max():.4f}")
    print(f"  Mean exposure: {county_df['observed_exposure'].mean():.4f}")
    print(f"  Std dev: {county_df['observed_exposure'].std():.4f}")

    print("\nTop 15 most exposed counties:")
    top = county_df.head(15)[["county_name", "fips", "observed_exposure", "total_employment"]]
    print(top.to_string(index=False))

    print("\nBottom 15 least exposed counties:")
    bottom = county_df.tail(15)[["county_name", "fips", "observed_exposure", "total_employment"]]
    print(bottom.to_string(index=False))

    # Save outputs
    parquet_path = PROC_DIR / "county_exposure.parquet"
    csv_path = PROC_DIR / "county_exposure.csv"
    county_df.to_parquet(parquet_path, index=False)
    county_df.to_csv(csv_path, index=False)
    print(f"\nSaved:\n  {parquet_path}\n  {csv_path}")

    return county_df


if __name__ == "__main__":
    main()
