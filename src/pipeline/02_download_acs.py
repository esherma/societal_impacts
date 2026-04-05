"""
Step 2: Pull ACS 5-year county-level occupation employment counts.

Uses ACS 2024 5-year estimates (2020–2024), table C24010:
  Civilian Employed Population 16+ by Sex and Occupation

We sum male + female to get total employment in each of 25 occupation categories.
These categories map to SOC major groups (2-digit SOC prefix).
"""

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
ACS_BASE = "https://api.census.gov/data/2024/acs/acs5"

# C24010 occupation leaf variables and their category names.
# Male variables (offset 0) + female variables (offset +36) = total.
# Each entry: (male_var_num, female_var_num, category_name, soc_prefix)
#   soc_prefix = first 2-3 digits of the SOC code that maps to this category.
#   Use tuples for categories that span multiple SOC groups.

OCC_CATEGORIES = [
    # (male_var_num, female_var_num, acs_label, soc_prefixes)
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


def build_variable_list() -> tuple[list[str], dict[str, str]]:
    """Return list of C24010 estimate variables to fetch, and a label map."""
    male_vars = []
    female_vars = []
    label_map = {}

    for male_num, female_num, label, _ in OCC_CATEGORIES:
        m_var = f"C24010_{male_num:03d}E"
        f_var = f"C24010_{female_num:03d}E"
        male_vars.append(m_var)
        female_vars.append(f_var)
        label_map[m_var] = label
        label_map[f_var] = label

    return male_vars + female_vars, label_map


def fetch_county_data(variables: list[str]) -> pd.DataFrame:
    """
    Fetch C24010 variables for all US counties.
    Census API caps at 50 variables per request, so we batch.
    """
    out_path = RAW_DIR / "acs_county_occupations_raw.parquet"
    if out_path.exists():
        print(f"  Using cached {out_path.name}")
        return pd.read_parquet(out_path)

    # Always fetch NAME, state, county
    base_cols = ["NAME"]
    all_records = None

    batch_size = 45  # stay well under 50-var limit
    batches = [variables[i:i+batch_size] for i in range(0, len(variables), batch_size)]
    print(f"  Fetching {len(variables)} variables in {len(batches)} batch(es) for all counties...")

    for i, batch in enumerate(batches):
        get_vars = ",".join(base_cols + batch)
        params = {
            "get": get_vars,
            "for": "county:*",
            "in": "state:*",
        }
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
                print(f"    Retry {attempt+1} after error: {e}")
                time.sleep(2)

        rows = resp.json()
        df_batch = pd.DataFrame(rows[1:], columns=rows[0])

        if all_records is None:
            all_records = df_batch
        else:
            # Join on state+county
            all_records = all_records.merge(
                df_batch.drop(columns=["NAME"]),
                on=["state", "county"],
                how="left",
            )

        print(f"    Batch {i+1}/{len(batches)} done ({df_batch.shape})")
        time.sleep(0.5)  # be polite

    all_records.to_parquet(out_path, index=False)
    print(f"  Saved to {out_path.name} ({all_records.shape})")
    return all_records


def aggregate_to_totals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sum male + female for each occupation category.
    Returns a tidy DataFrame: FIPS, county_name, occ_category, employment.
    """
    records = []
    for male_num, female_num, label, soc_prefixes in OCC_CATEGORIES:
        m_var = f"C24010_{male_num:03d}E"
        f_var = f"C24010_{female_num:03d}E"

        for _, row in df.iterrows():
            try:
                m_val = int(row[m_var]) if row[m_var] not in ("-666666666", None, "") else 0
                f_val = int(row[f_var]) if row[f_var] not in ("-666666666", None, "") else 0
            except (ValueError, TypeError):
                m_val, f_val = 0, 0

            total = m_val + f_val
            if total < 0:
                total = 0

            fips = row["state"] + row["county"]
            records.append({
                "fips": fips,
                "county_name": row["NAME"],
                "occ_category": label,
                "soc_prefixes": "|".join(soc_prefixes),
                "employment": total,
            })

    return pd.DataFrame(records)


def main():
    variables, label_map = build_variable_list()
    print(f"ACS C24010 variables to fetch: {len(variables)}")

    raw_df = fetch_county_data(variables)
    print(f"Raw ACS data: {raw_df.shape}")

    print("Aggregating male + female counts...")
    tidy = aggregate_to_totals(raw_df)
    print(f"Tidy shape: {tidy.shape}")
    print(f"Counties: {tidy['fips'].nunique()}")
    print(f"Occupation categories: {tidy['occ_category'].nunique()}")

    out_path = RAW_DIR / "acs_county_occupations_tidy.parquet"
    tidy.to_parquet(out_path, index=False)
    print(f"Saved to {out_path}")

    # Sanity check
    sample = tidy[tidy["fips"] == "06001"].set_index("occ_category")["employment"]
    print("\nSample: Alameda County, CA employment by occupation category:")
    print(sample.sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
