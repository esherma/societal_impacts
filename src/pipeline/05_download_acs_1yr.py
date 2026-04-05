"""
Step 5: Pull ACS 1-year 2024 county occupation data.

ACS 1-year covers counties with population ≥ 65,000 (~861 counties).
Uses the same C24010 table as the 5-year data for comparability.
"""

import os
import time
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
ACS_BASE = "https://api.census.gov/data/2024/acs/acs1"

# Same OCC_CATEGORIES as in 02_download_acs.py — must stay in sync
OCC_CATEGORIES = [
    (5,  41, "Management occupations",                               ["11-"]),
    (6,  42, "Business and financial operations occupations",        ["13-"]),
    (8,  44, "Computer and mathematical occupations",                ["15-"]),
    (9,  45, "Architecture and engineering occupations",             ["17-"]),
    (10, 46, "Life, physical, and social science occupations",       ["19-"]),
    (12, 48, "Community and social service occupations",             ["21-"]),
    (13, 49, "Legal occupations",                                    ["23-"]),
    (14, 50, "Educational instruction and library occupations",      ["25-"]),
    (15, 51, "Arts, design, entertainment, sports, media occupations", ["27-"]),
    (17, 53, "Health diagnosing and treating practitioners",         ["29-1"]),
    (18, 54, "Health technologists and technicians",                 ["29-2"]),
    (20, 56, "Healthcare support occupations",                       ["31-"]),
    (22, 58, "Firefighting and prevention workers",                  ["33-1", "33-2"]),
    (23, 59, "Law enforcement workers",                              ["33-3", "33-9"]),
    (24, 60, "Food preparation and serving occupations",             ["35-"]),
    (25, 61, "Building and grounds cleaning and maintenance",        ["37-"]),
    (26, 62, "Personal care and service occupations",                ["39-"]),
    (28, 64, "Sales and related occupations",                        ["41-"]),
    (29, 65, "Office and administrative support occupations",        ["43-"]),
    (31, 67, "Farming, fishing, and forestry occupations",           ["45-"]),
    (32, 68, "Construction and extraction occupations",              ["47-"]),
    (33, 69, "Installation, maintenance, and repair occupations",    ["49-"]),
    (35, 71, "Production occupations",                               ["51-"]),
    (36, 72, "Transportation occupations",                           ["53-1", "53-2", "53-3", "53-4", "53-5", "53-6"]),
    (37, 73, "Material moving occupations",                          ["53-7"]),
]


def build_variable_list():
    male_vars = [f"C24010_{num:03d}E" for num, _, _, _ in OCC_CATEGORIES]
    female_vars = [f"C24010_{num:03d}E" for _, num, _, _ in OCC_CATEGORIES]
    return male_vars + female_vars


def fetch_county_data(variables):
    out_path = RAW_DIR / "acs_1yr_county_occupations_raw.parquet"
    if out_path.exists():
        print(f"  Using cached {out_path.name}")
        return pd.read_parquet(out_path)

    batch_size = 45
    batches = [variables[i:i+batch_size] for i in range(0, len(variables), batch_size)]
    print(f"  Fetching {len(variables)} variables in {len(batches)} batch(es) for all available counties...")

    all_records = None
    for i, batch in enumerate(batches):
        get_vars = ",".join(["NAME"] + batch)
        params = {"get": get_vars, "for": "county:*", "in": "state:*"}
        if CENSUS_API_KEY:
            params["key"] = CENSUS_API_KEY

        for attempt in range(3):
            try:
                resp = requests.get(ACS_BASE, params=params, timeout=60)
                resp.raise_for_status()
                break
            except requests.RequestException as e:
                if attempt == 2:
                    raise
                time.sleep(2)

        rows = resp.json()
        df_batch = pd.DataFrame(rows[1:], columns=rows[0])

        if all_records is None:
            all_records = df_batch
        else:
            all_records = all_records.merge(
                df_batch.drop(columns=["NAME"]), on=["state", "county"], how="left"
            )
        print(f"    Batch {i+1}/{len(batches)} done: {df_batch.shape[0]} counties")
        time.sleep(0.5)

    all_records.to_parquet(out_path, index=False)
    print(f"  Saved {out_path.name}: {all_records.shape}")
    return all_records


def aggregate_to_totals(df):
    records = []
    for male_num, female_num, label, soc_prefixes in OCC_CATEGORIES:
        m_var = f"C24010_{male_num:03d}E"
        f_var = f"C24010_{female_num:03d}E"
        for _, row in df.iterrows():
            try:
                m = int(row[m_var]) if row[m_var] not in ("-666666666", None, "") else 0
                f = int(row[f_var]) if row[f_var] not in ("-666666666", None, "") else 0
            except (ValueError, TypeError):
                m, f = 0, 0
            total = max(0, m + f)
            records.append({
                "fips": row["state"] + row["county"],
                "county_name": row["NAME"],
                "occ_category": label,
                "soc_prefixes": "|".join(soc_prefixes),
                "employment": total,
            })
    return pd.DataFrame(records)


def main():
    variables = build_variable_list()
    print(f"Downloading ACS 1-year 2024 occupation data...")
    raw = fetch_county_data(variables)
    print(f"Counties available in ACS 1-year: {raw.shape[0]}")

    tidy = aggregate_to_totals(raw)
    out = RAW_DIR / "acs_1yr_county_occupations_tidy.parquet"
    tidy.to_parquet(out, index=False)
    print(f"Saved: {out}")
    print(f"Counties: {tidy['fips'].nunique()}, Categories: {tidy['occ_category'].nunique()}")


if __name__ == "__main__":
    main()
