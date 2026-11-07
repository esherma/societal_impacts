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
uv run python 06_tract_exposure.py      # National census-tract exposure from ACS bulk Summary File (no API key)
uv run python 07_robot_exposure.py      # Robot exposure index + employment weights (county + tract)
uv run python 08_geographic_variance.py # Within- vs between-county variance; per-county tract spread
uv run python 04_export_for_map.py      # Export to src/map/data/atlas.json + rankings.json (run last)
```

Scripts cache their outputs — re-running a step skips the download if the output file already exists. Large bulk downloads (Census summary files) go to `data/raw/_cache/`, which is gitignored.

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

Step 7 (robot_exposure.py)  HF robot_exposure/ + ACS 2024 1-yr B24114 national employment + Census 2018 occ crosswalk
  → data/raw/robot_exposure/robot_exposure_occupations.csv
  → data/processed/occ_category_scores.csv       (25 groups × ai/robot × unweighted/emp-weighted)
  → data/processed/soc_employment_weights.csv
  → data/processed/county_dual_exposure.parquet  (ai, ai_w, robot, robot_w per county, 5yr + 1yr)
  → adds ai_w, robot, robot_w to tract_exposure.parquet

Step 8 (geographic_variance.py)  uses tract file + C24010 margins of error
  → data/processed/geographic_variance.json      (within/between decomposition, noise-adjusted)
  → data/processed/county_within_spread.parquet  (per-county tract SD, AI + robot)

Step 4 reads step 7/8 outputs if present: atlas.json gains `occ_robot`, `summary_robot_*`,
and per-county `r` (robot index) and `ws` ([sd_ai, sd_robot, n_tracts]).
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
- Four layers via `#layer-toggle` (`LAYERS` in `map.js`): AI exposure (Blues), robot exposure (RdPu, 0–3 scale), AI × Robot (3×3 bivariate by national terciles), within-county spread (Greens; only counties with ≥10 tracts).
- The map's AI and robot indices both use **unweighted** category means (the published method). Employment-weighted variants (`ai_w`, `robot_w`) exist in the processed data for sensitivity checks only.
- Clicking a county opens a detail panel showing per-occupation contributions (`sh[i] * occ_exp[i]`).
## Key Constraint

The `OCC_CATEGORY_ORDER` in `04_export_for_map.py` and the `OCC_CATEGORIES` tuple list in `02_download_acs.py` / `05_download_acs_1yr.py` must all stay consistent — array positions are used for indexing in both Python and JavaScript. `06_tract_exposure.py`, `07_robot_exposure.py` and `08_geographic_variance.py` import `OCC_CATEGORIES` from `02_download_acs.py` directly, so they follow automatically.
