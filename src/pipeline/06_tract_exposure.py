"""
Step 6: Census-tract-level AI exposure index (national).

Same Bartik shift-share as step 3, but at the census-tract level, using the ACS
table-based Summary File bulk downloads from www2.census.gov instead of the Census
API. (As of Nov 2026 the API rejects requests without a key; the bulk files do not
need one and contain every geography, including all ~85k tracts.)

Inputs (downloaded and cached in data/raw/_cache/, gitignored — ~350 MB):
  acsdt5y2024-c24010.dat   Sex by Occupation (25 leaf groups, same as county pipeline)
  acsdt5y2024-b15003.dat   Educational attainment, 25+  (control: BA+ share)
  acsdt5y2024-b19013.dat   Median household income      (control)

Output:
  data/processed/tract_exposure.parquet   one row per tract, national

Caveat: tract-level C24010 estimates are noisy (median tract has ~2k workers and the
25-group margins of error are large). Treat any single tract's score as approximate;
aggregate (or cluster standard errors by tract) before drawing inferences.
"""

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).parent.parent.parent
RAW_DIR = ROOT / "data" / "raw"
CACHE_DIR = RAW_DIR / "_cache"
PROC_DIR = ROOT / "data" / "processed"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)

ACS_VINTAGE = 2024  # 2020–2024 5-year. Bump to 2025 once the 2021–2025 5-year drops (~Dec 2026).
SF_BASE = (f"https://www2.census.gov/programs-surveys/acs/summary_file/{ACS_VINTAGE}"
           f"/table-based-SF/data/5YRData")

# Reuse the canonical category list from step 2 so the ordering can't drift.
_spec = importlib.util.spec_from_file_location("acs02", Path(__file__).parent / "02_download_acs.py")
_acs02 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_acs02)
OCC_CATEGORIES = _acs02.OCC_CATEGORIES


def download(table: str) -> Path:
    name = f"acsdt5y{ACS_VINTAGE}-{table}.dat"
    out = CACHE_DIR / name
    if out.exists():
        print(f"  Using cached {name}")
        return out
    url = f"{SF_BASE}/{name}"
    print(f"  Downloading {url} ...")
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        tmp = out.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.rename(out)
    return out


def read_tracts(path: Path, cols: list[str]) -> pd.DataFrame:
    """Stream a summary-file table, keeping only census-tract rows (GEO_ID 1400000US…)."""
    keep = []
    for chunk in pd.read_csv(path, sep="|", usecols=["GEO_ID"] + cols, dtype=str, chunksize=200_000):
        keep.append(chunk[chunk["GEO_ID"].str.startswith("1400000US")])
    df = pd.concat(keep, ignore_index=True)
    df["geoid"] = df["GEO_ID"].str[9:]  # 11-digit state+county+tract
    df = df.drop(columns="GEO_ID")
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main():
    print(f"ACS {ACS_VINTAGE} 5-year summary-file tables")
    occ_path = download("c24010")
    edu_path = download("b15003")
    inc_path = download("b19013")

    # ── Occupation shares ────────────────────────────────────────────
    occ_cols = []
    for m, f, _, _ in OCC_CATEGORIES:
        occ_cols += [f"C24010_E{m:03d}", f"C24010_E{f:03d}"]
    occ = read_tracts(occ_path, ["C24010_E001", "C24010_M001"] + occ_cols)
    print(f"  {len(occ):,} tracts in C24010")

    emp = np.column_stack([
        occ[f"C24010_E{m:03d}"].fillna(0).clip(lower=0) + occ[f"C24010_E{f:03d}"].fillna(0).clip(lower=0)
        for m, f, _, _ in OCC_CATEGORIES
    ])
    total = emp.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        shares = emp / total[:, None]

    cw = pd.read_csv(PROC_DIR / "occ_category_crosswalk.csv").set_index("occ_category")["category_exposure"]
    occ_exp = np.array([cw[label] for _, _, label, _ in OCC_CATEGORIES])
    exposure = shares @ occ_exp

    out = pd.DataFrame({
        "geoid": occ["geoid"],
        "state_fips": occ["geoid"].str[:2],
        "county_fips5": occ["geoid"].str[:5],
        "workers": total.astype(int),
        "workers_moe": occ["C24010_M001"],
        "exposure": np.where(total > 0, exposure, np.nan),
    })
    for i, (_, _, label, _) in enumerate(OCC_CATEGORIES):
        out[f"sh_{i:02d}"] = np.round(shares[:, i], 5)

    # ── Controls ─────────────────────────────────────────────────────
    edu = read_tracts(edu_path, ["B15003_E001", "B15003_E022", "B15003_E023", "B15003_E024", "B15003_E025"])
    edu["ba_plus"] = edu[["B15003_E022", "B15003_E023", "B15003_E024", "B15003_E025"]].sum(axis=1) \
        / edu["B15003_E001"].replace(0, np.nan)
    edu["adults_25p"] = edu["B15003_E001"]
    inc = read_tracts(inc_path, ["B19013_E001"])
    inc["median_hh_income"] = inc["B19013_E001"].where(inc["B19013_E001"] > 0)

    out = (out.merge(edu[["geoid", "ba_plus", "adults_25p"]], on="geoid", how="left")
              .merge(inc[["geoid", "median_hh_income"]], on="geoid", how="left"))

    # Reliability flag: <500 workers → too noisy to interpret on its own
    out["low_reliability"] = out["workers"] < 500

    path = PROC_DIR / "tract_exposure.parquet"
    out.to_parquet(path, index=False)
    v = out.dropna(subset=["exposure"])
    print(f"\nSaved {path} ({len(out):,} tracts; {v['low_reliability'].sum():,} flagged <500 workers)")
    print(f"  exposure p05/p50/p95: {v['exposure'].quantile([.05, .5, .95]).round(4).tolist()}")
    print(f"  corr(exposure, BA+): {v[['exposure', 'ba_plus']].corr().iloc[0, 1]:.3f}")

    # Sanity: tract worker totals should roll up to the county pipeline's totals
    county = pd.read_parquet(RAW_DIR / "acs_county_occupations_tidy.parquet") \
        .groupby("fips")["employment"].sum()
    roll = out.groupby("county_fips5")["workers"].sum()
    joined = pd.concat([roll, county], axis=1, keys=["tract_sum", "county"]).dropna()
    rel = (joined["tract_sum"] / joined["county"] - 1).abs()
    print(f"  tract→county worker roll-up: median abs diff {rel.median():.2%}, max {rel.max():.2%}")


if __name__ == "__main__":
    main()
