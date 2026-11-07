"""
Step 7: Download precinct-level election results + precinct boundaries (prototype: King County, WA).

Why King County first: it publishes machine-readable precinct CSVs within hours of the
polls closing (WA is all-mail, so the count is unusually complete early), boundary files
for every year via ArcGIS REST, and it has wide within-county variation in AI exposure
(Seattle/Eastside tech vs. south-county logistics and manufacturing).

Results files are snapshots. King County publishes three precinct-level drops per
general election: election night → "mid-election" (ballots counted by the Friday after
Election Day) → final (certification, ~3 weeks out). Edit RESULTS below as new drops
appear and re-run with --refresh. The analysis compares like-with-like: the 2026
election-night snapshot against the 2024 election-night snapshot, because late-counted
WA ballots skew younger and more Democratic, and that skew isn't uniform across precincts.

Outputs (data/raw/_cache/elections/, gitignored):
  king_<year>_<snapshot>.csv          raw King County precinct results
  king_votdst_<year>.geojson          precinct polygons (EPSG:4326)
"""

import argparse
import json
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent.parent
OUT_DIR = ROOT / "data" / "raw" / "_cache" / "elections"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CDN = "https://cdn.kingcounty.gov/-/media/king-county/depts/elections/results"

# (year, snapshot) → URL. Find new links on
# https://kingcounty.gov/en/dept/elections/results/2026/november-general
RESULTS = {
    (2026, "election_night"): f"{CDN}/2026/11/election-night-results-report.csv",
    # (2026, "mid"):   f"{CDN}/2026/11/<mid-election file>.csv",     # due ~Nov 2026
    # (2026, "final"): f"{CDN}/2026/11/final-results-report.csv",    # due ~Nov 25 2026
    (2024, "election_night"): f"{CDN}/2024/11/election-night-results-report.csv",
    (2024, "final"): f"{CDN}/2024/11/final-results-report.csv",
}

ARCGIS = "https://services.arcgis.com/Ej0PsM5Aw677QF1W/arcgis/rest/services"
BOUNDARIES = {
    2026: f"{ARCGIS}/VOTDST_AREA_418/FeatureServer/0",        # current precincts
    2024: f"{ARCGIS}/VOTDST_2024_AREA_3068/FeatureServer/0",
}


def fetch(url: str, out: Path, refresh: bool):
    if out.exists() and not refresh:
        print(f"  cached  {out.name}")
        return
    print(f"  GET     {url}")
    r = requests.get(url, timeout=300, headers={"User-Agent": "ai-impact-atlas/0.1"})
    r.raise_for_status()
    out.write_bytes(r.content)
    print(f"  saved   {out.name} ({len(r.content) / 1e6:.1f} MB)")


def fetch_features(layer_url: str, out: Path, refresh: bool):
    """Page through an ArcGIS FeatureServer layer and save as one GeoJSON (WGS84)."""
    if out.exists() and not refresh:
        print(f"  cached  {out.name}")
        return
    features, offset, page = [], 0, 1000
    while True:
        params = {
            "where": "1=1", "outFields": "votdst,NAME,SUM_VOTERS", "outSR": 4326,
            "f": "geojson", "resultOffset": offset, "resultRecordCount": page,
        }
        r = requests.get(f"{layer_url}/query", params=params, timeout=120)
        r.raise_for_status()
        batch = r.json().get("features", [])
        features += batch
        if len(batch) < page:
            break
        offset += page
    out.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    print(f"  saved   {out.name} ({len(features):,} precincts)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-download even if cached")
    args = ap.parse_args()

    print("Precinct results:")
    for (year, snap), url in RESULTS.items():
        fetch(url, OUT_DIR / f"king_{year}_{snap}.csv", args.refresh)

    print("Precinct boundaries:")
    for year, url in BOUNDARIES.items():
        fetch_features(url, OUT_DIR / f"king_votdst_{year}.geojson", args.refresh)

    print("Tract boundaries (TIGER 2024, WA):")
    fetch("https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_53_tract.zip",
          OUT_DIR / "tl_2024_53_tract.zip", args.refresh)


if __name__ == "__main__":
    main()
