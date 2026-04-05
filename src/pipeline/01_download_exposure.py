"""
Step 1: Download and inspect Anthropic labor_market_impacts data from HuggingFace.

Dataset: Anthropic/EconomicIndex
Path: labor_market_impacts/
"""

import json
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download, list_repo_files

RAW_DIR = Path(__file__).parent.parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

REPO_ID = "Anthropic/EconomicIndex"
REPO_TYPE = "dataset"


def list_available_files():
    print(f"Listing files in {REPO_ID}...")
    files = list(list_repo_files(REPO_ID, repo_type=REPO_TYPE))
    for f in sorted(files):
        print(f"  {f}")
    return files


def download_file(repo_path: str) -> Path:
    local_path = RAW_DIR / Path(repo_path).name
    if local_path.exists():
        print(f"  Already downloaded: {local_path.name}")
        return local_path
    print(f"  Downloading {repo_path}...")
    downloaded = hf_hub_download(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        filename=repo_path,
        local_dir=str(RAW_DIR),
    )
    return Path(downloaded)


def inspect_dataframe(df: pd.DataFrame, name: str):
    print(f"\n=== {name} ===")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nDtypes:\n{df.dtypes}")
    print(f"\nFirst 3 rows:\n{df.head(3).to_string()}")
    if any("soc" in c.lower() or "occ" in c.lower() for c in df.columns):
        soc_cols = [c for c in df.columns if "soc" in c.lower() or "occ" in c.lower()]
        print(f"\nOccupation-related columns: {soc_cols}")
        for col in soc_cols:
            sample = df[col].dropna().head(5).tolist()
            print(f"  {col} sample: {sample}")
    exposure_cols = [
        c for c in df.columns
        if any(kw in c.lower() for kw in ["exposure", "beta", "score", "automat", "augment"])
    ]
    if exposure_cols:
        print(f"\nExposure-related columns: {exposure_cols}")
        print(df[exposure_cols].describe())


def main():
    files = list_available_files()

    # Filter to labor_market_impacts files
    lmi_files = [f for f in files if "labor_market" in f.lower()]
    print(f"\nLabor market impact files found: {lmi_files}")

    if not lmi_files:
        print("No labor_market_impacts files found. Downloading all files for inspection.")
        lmi_files = files

    downloaded_paths = {}
    for repo_path in lmi_files:
        try:
            local = download_file(repo_path)
            downloaded_paths[repo_path] = local
        except Exception as e:
            print(f"  Error downloading {repo_path}: {e}")

    # Inspect each downloaded file
    summary = {}
    for repo_path, local_path in downloaded_paths.items():
        suffix = local_path.suffix.lower()
        try:
            if suffix == ".parquet":
                df = pd.read_parquet(local_path)
            elif suffix == ".csv":
                df = pd.read_csv(local_path)
            elif suffix == ".json":
                with open(local_path) as f:
                    data = json.load(f)
                print(f"\n=== {local_path.name} (JSON) ===")
                if isinstance(data, list):
                    print(f"  List of {len(data)} items")
                    print(f"  First item keys: {list(data[0].keys()) if data else 'empty'}")
                else:
                    print(f"  Keys: {list(data.keys())}")
                continue
            else:
                print(f"  Skipping {local_path.name} (unsupported format {suffix})")
                continue

            inspect_dataframe(df, local_path.name)
            summary[local_path.name] = {
                "rows": len(df),
                "columns": list(df.columns),
            }

        except Exception as e:
            print(f"  Error reading {local_path.name}: {e}")

    # Save summary
    summary_path = RAW_DIR / "exposure_data_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to {summary_path}")


if __name__ == "__main__":
    main()
