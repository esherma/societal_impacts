#!/usr/bin/env bash
# Build src/map/data/counties-2023.json: county + state TopoJSON from the Census
# 2023 cartographic boundary file. Uses 2023 county codes, so Connecticut's
# planning regions (09110-09190) and Alaska's Chugach/Copper River (02063/02066)
# match the ACS data. Territories (STATEFP >= 60) are dropped; geoAlbersUsa
# can't draw them anyway. Needs curl, unzip and npx (Node).
set -euo pipefail
cd "$(dirname "$0")"
CACHE=../../data/raw/_cache/cb_2023_us_county_5m
OUT=../map/data/counties-2023.json
mkdir -p "$CACHE"
if [ ! -f "$CACHE/cb_2023_us_county_5m.shp" ]; then
  curl -sSfL -o "$CACHE/cb.zip" https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_5m.zip
  unzip -oq "$CACHE/cb.zip" -d "$CACHE"
fi
npx --yes mapshaper@0.6.102 "$CACHE/cb_2023_us_county_5m.shp" \
  -filter 'STATEFP < "60"' \
  -simplify 25% keep-shapes \
  -filter-fields GEOID,STATEFP \
  -rename-layers counties \
  -dissolve STATEFP + name=states \
  -filter-fields GEOID target=counties \
  -o target=counties,states format=topojson id-field=GEOID,STATEFP quantization=100000 force "$OUT"
