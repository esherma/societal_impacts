# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI Impact Atlas** — a county-level interactive choropleth map showing AI labor market exposure across the US. Built from a Bartik shift-share index combining Anthropic's occupation-level AI exposure scores (from HuggingFace) with ACS workforce composition data from the Census API.

## Running the Pipeline

The pipeline lives in `src/pipeline/` and is managed with `uv`. The `.venv` is located at `src/pipeline/.venv/`.

```bash
cd src/pipeline
uv run python 01_download_exposure.py   # Download Anthropic EconomicIndex from HuggingFace
uv run python 02_download_acs.py        # Download ACS 5-year county occupation data
uv run python 05_download_acs_1yr.py    # Download ACS 1-year data (~861 large counties)
uv run python 03_compute_index.py       # Compute Bartik shift-share exposure index
uv run python 04_export_for_map.py      # Export to src/map/data/atlas.json + rankings.json

# Tract-level index + election overlay (King County prototype)
uv run python 06_tract_exposure.py      # National tract exposure from ACS bulk Summary File (no API key)
uv run python 07_download_elections.py  # King County precinct results + boundaries (--refresh for new drops)
uv run python 08_election_overlay.py    # Crosswalks, tract-level models, src/map/data/elections/king_2026.json
```

Scripts cache their outputs — re-running a step skips the download if the output file already exists. Large bulk downloads (Census summary files, election CSVs, shapes) go to `data/raw/_cache/`, which is gitignored.

As of Nov 2026 the Census API rejects requests without a key (302 → `missing_key`). Steps 2/5 need `CENSUS_API_KEY`; step 6 uses the bulk Summary File on www2.census.gov and needs no key:
```bash
export CENSUS_API_KEY=your_key_here
```

## Running the Map

No build step. Serve `src/map/` over HTTP (required for D3 JSON fetches):

```bash
cd src/map && python -m http.server 8000
```

Then open `http://localhost:8000`. The map fetches US county TopoJSON from a CDN plus local `data/atlas.json`.

## Data Flow

```
HuggingFace (Anthropic/EconomicIndex)
  → data/raw/labor_market_impacts/job_exposure.csv

Census ACS API (C24010 table)
  → data/raw/acs_county_occupations_raw.parquet       (5-year, all 3,222 counties)
  → data/raw/acs_1yr_county_occupations_raw.parquet   (1-year, ~861 counties)
  → data/raw/acs_county_occupations_tidy.parquet
  → data/raw/acs_1yr_county_occupations_tidy.parquet

Step 3 (compute_index.py)
  → data/processed/county_exposure.parquet/.csv
  → data/processed/occ_category_crosswalk.csv

Step 4 (export_for_map.py)
  → src/map/data/atlas.json      (main map payload: counties_5yr, counties_1yr, occ scores)
  → src/map/data/rankings.json   (top/bottom 15 counties per dataset)

Step 6 (tract_exposure.py)  ACS Summary File C24010/B15003/B19013, 2020–24 5-year
  → data/processed/tract_exposure.parquet   (85k tracts: exposure, sh_00..sh_24, ba_plus, income)

Step 7 (download_elections.py)  King County Elections CSVs + KC GIS VOTDST + TIGER tracts
  → data/raw/_cache/elections/

Step 8 (election_overlay.py)
  → data/processed/king_precinct_overlay.parquet, king_tract_overlay.parquet
  → src/map/data/elections/king_2026.json   (precinct + tract GeoJSON, models, binned scatter)
```

## Architecture

### Python Pipeline (`src/pipeline/`)

- **`02_download_acs.py` and `05_download_acs_1yr.py`** share a hardcoded `OCC_CATEGORIES` list mapping 25 ACS C24010 occupation groups to SOC prefixes. Both files must stay in sync.
- **`03_compute_index.py`** maps each ACS category to a mean `observed_exposure` score (simple average across matching SOC codes), then computes a workforce-share-weighted sum per county.
- **`04_export_for_map.py`** exports the final `atlas.json`. The `OCC_CATEGORY_ORDER` list in this file must match the order in the ACS download scripts — the browser uses array indexing into `sh[]` (workforce shares) against `occ_exp[]` (category exposure scores).

### Web Map (`src/map/`)

- Pure D3 v7 + TopoJSON (CDN). No bundler or build step.
- `map.js` loads `atlas.json` and US county TopoJSON, renders a choropleth with a sequential blue color scale clamped to p05–p95.
- Two datasets switchable via toggle: 5-year (all counties) and 1-year (large counties only).
- Clicking a county opens a detail panel showing per-occupation contributions (`sh[i] * occ_exp[i]`).
- `elections.html` / `elections.js` is a separate page (King County 2026 midterms overlay). Geometry is plain GeoJSON with **clockwise** exterior rings (d3-geo convention; step 8 enforces this with `shapely.orient_polygons`).
- Election-overlay inference is at the **tract** level (where exposure is measured); precincts are display-only. See `Claude_Proposals/impact_atlas/04_election_overlay.md`.

## Key Constraint

The `OCC_CATEGORY_ORDER` in `04_export_for_map.py` and the `OCC_CATEGORIES` tuple list in `02_download_acs.py` / `05_download_acs_1yr.py` must all stay consistent — array positions are used for indexing in both Python and JavaScript. `06_tract_exposure.py` imports `OCC_CATEGORIES` from `02_download_acs.py` directly, so it follows automatically.
