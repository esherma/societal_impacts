"""
Step 4: Export county exposure data as a single JSON for the interactive map.

Produces src/map/data/atlas.json with structure:
{
  "occ_names": [...25 names...],
  "occ_exp":   [...25 category exposure scores...],
  "summary_5yr": { min, max, mean, median, p05, p10, p25, p75, p90, p95, n },
  "summary_1yr": { ... },
  "counties_5yr": {
    "51013": { "e": 0.149, "n": "Arlington County", "s": "Virginia",
               "w": 145584, "sh": [...25 workforce shares...] }
  },
  "counties_1yr": { ... same structure, ~861 counties ... }
}

The browser computes contribution_i = sh[i] * occ_exp[i].
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
PROC_DIR = Path(__file__).parent.parent.parent / "data" / "processed"
MAP_DATA_DIR = Path(__file__).parent.parent / "map" / "data"
MAP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Must match the OCC_CATEGORIES order in 02_download_acs.py / 05_download_acs_1yr.py
OCC_CATEGORY_ORDER = [
    "Management occupations",
    "Business and financial operations occupations",
    "Computer and mathematical occupations",
    "Architecture and engineering occupations",
    "Life, physical, and social science occupations",
    "Community and social service occupations",
    "Legal occupations",
    "Educational instruction and library occupations",
    "Arts, design, entertainment, sports, media occupations",
    "Health diagnosing and treating practitioners",
    "Health technologists and technicians",
    "Healthcare support occupations",
    "Firefighting and prevention workers",
    "Law enforcement workers",
    "Food preparation and serving occupations",
    "Building and grounds cleaning and maintenance",
    "Personal care and service occupations",
    "Sales and related occupations",
    "Office and administrative support occupations",
    "Farming, fishing, and forestry occupations",
    "Construction and extraction occupations",
    "Installation, maintenance, and repair occupations",
    "Production occupations",
    "Transportation occupations",
    "Material moving occupations",
]


def load_crosswalk() -> dict[str, float]:
    """Load the category → exposure score crosswalk."""
    cw = pd.read_csv(PROC_DIR / "occ_category_crosswalk.csv")
    return dict(zip(cw["occ_category"], cw["category_exposure"]))


def compute_county_records(tidy_df: pd.DataFrame, occ_exp: list[float]) -> dict:
    """
    For each county, compute:
      - total shift-share exposure index
      - workforce shares for all 25 occupation categories
    Returns dict keyed by 5-digit FIPS.
    """
    # Pivot to (fips × occ_category) matrix
    pivot = tidy_df.pivot_table(
        index="fips", columns="occ_category", values="employment", aggfunc="sum", fill_value=0
    )
    # Ensure columns are in the canonical order
    for cat in OCC_CATEGORY_ORDER:
        if cat not in pivot.columns:
            pivot[cat] = 0
    pivot = pivot[OCC_CATEGORY_ORDER]

    # Get county name from tidy (first occurrence)
    county_meta = tidy_df.groupby("fips")[["county_name"]].first()
    county_meta["fips"] = county_meta.index

    totals = pivot.sum(axis=1)
    shares = pivot.div(totals.replace(0, np.nan), axis=0).fillna(0)

    # Shift-share exposure
    occ_exp_arr = np.array(occ_exp)
    exposure = shares.values @ occ_exp_arr  # dot product per county

    records = {}
    for fips in pivot.index:
        fips_str = str(fips).zfill(5)
        raw_name = county_meta.loc[fips, "county_name"]
        # Split "Alameda County, California" → county_name, state
        parts = str(raw_name).split(", ", 1)
        county_short = parts[0]
        state = parts[1] if len(parts) > 1 else ""

        sh = [round(float(v), 5) for v in shares.loc[fips].values]

        records[fips_str] = {
            "e": round(float(exposure[pivot.index.get_loc(fips)]), 6),
            "n": county_short,
            "s": state,
            "w": int(totals[fips]),
            "sh": sh,
        }

    return records


def summary_stats(records: dict) -> dict:
    exposures = [v["e"] for v in records.values() if v["e"] > 0]
    arr = np.array(exposures)
    return {
        "n": len(records),
        "min": round(float(np.min(arr)), 6),
        "max": round(float(np.max(arr)), 6),
        "mean": round(float(np.mean(arr)), 6),
        "median": round(float(np.median(arr)), 6),
        "p05": round(float(np.percentile(arr, 5)), 6),
        "p10": round(float(np.percentile(arr, 10)), 6),
        "p25": round(float(np.percentile(arr, 25)), 6),
        "p75": round(float(np.percentile(arr, 75)), 6),
        "p90": round(float(np.percentile(arr, 90)), 6),
        "p95": round(float(np.percentile(arr, 95)), 6),
    }


def main():
    print("Loading crosswalk...")
    cw = load_crosswalk()
    occ_exp = [round(float(cw.get(cat, 0.0)), 6) for cat in OCC_CATEGORY_ORDER]
    print(f"  {len([e for e in occ_exp if e > 0])} categories with exposure data")

    print("Building 5-year county records...")
    tidy_5yr = pd.read_parquet(RAW_DIR / "acs_county_occupations_tidy.parquet")
    counties_5yr = compute_county_records(tidy_5yr, occ_exp)
    stats_5yr = summary_stats(counties_5yr)
    print(f"  {len(counties_5yr)} counties, mean={stats_5yr['mean']:.4f}, "
          f"range=[{stats_5yr['min']:.4f}, {stats_5yr['max']:.4f}]")

    print("Building 1-year county records...")
    tidy_1yr = pd.read_parquet(RAW_DIR / "acs_1yr_county_occupations_tidy.parquet")
    counties_1yr = compute_county_records(tidy_1yr, occ_exp)
    stats_1yr = summary_stats(counties_1yr)
    print(f"  {len(counties_1yr)} counties, mean={stats_1yr['mean']:.4f}, "
          f"range=[{stats_1yr['min']:.4f}, {stats_1yr['max']:.4f}]")

    # Build atlas
    atlas = {
        "occ_names": OCC_CATEGORY_ORDER,
        "occ_exp": occ_exp,
        "summary_5yr": stats_5yr,
        "summary_1yr": stats_1yr,
        "counties_5yr": counties_5yr,
        "counties_1yr": counties_1yr,
    }

    out_path = MAP_DATA_DIR / "atlas.json"
    with open(out_path, "w") as f:
        json.dump(atlas, f, separators=(",", ":"))

    size_kb = out_path.stat().st_size / 1024
    print(f"\nSaved atlas.json ({size_kb:.0f} KB)")

    # Top 10 / bottom 10 for each dataset (used in rankings panel)
    def top_bottom(records, n=15):
        sorted_items = sorted(records.items(), key=lambda x: x[1]["e"], reverse=True)
        top = [{"fips": k, "county": v["n"], "state": v["s"], "exposure": v["e"], "rank": i+1}
               for i, (k, v) in enumerate(sorted_items[:n])]
        bottom = [{"fips": k, "county": v["n"], "state": v["s"], "exposure": v["e"], "rank": len(records)-n+i+1}
                  for i, (k, v) in enumerate(sorted_items[-n:])]
        return top, bottom

    top5, bot5 = top_bottom(counties_5yr)
    top1, bot1 = top_bottom(counties_1yr)

    rankings = {
        "5yr": {"top": top5, "bottom": bot5},
        "1yr": {"top": top1, "bottom": bot1},
    }
    rankings_path = MAP_DATA_DIR / "rankings.json"
    with open(rankings_path, "w") as f:
        json.dump(rankings, f, indent=2)
    print(f"Saved rankings.json")


if __name__ == "__main__":
    main()
