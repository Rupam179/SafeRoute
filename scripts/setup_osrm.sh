#!/usr/bin/env bash
# ============================================================================
# SafeRoute — OSRM data preparation
# ============================================================================
# OSRM needs a pre-processed .osrm dataset before it can serve routes.
# This is a ONE-TIME step (re-run only if you change region or OSM version).
# Run this from the project root: bash scripts/setup_osrm.sh
#
# Default region: West Bengal (covers Kolkata). Change REGION_URL to match
# your team's target city — smaller extracts process much faster.
# Browse extracts at: https://download.geofabrik.de/asia/india.html
# ============================================================================
set -euo pipefail

REGION_URL="${1:-https://download.geofabrik.de/asia/india/west-bengal-latest.osm.pbf}"
DATA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/osrm-data"
PBF_NAME="region.osm.pbf"

mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

if [ ! -f "$PBF_NAME" ]; then
  echo "Downloading OSM extract from: $REGION_URL"
  curl -L -o "$PBF_NAME" "$REGION_URL"
else
  echo "Found existing $PBF_NAME, skipping download."
fi

echo "Extracting (car profile)..."
docker run --rm -t -v "$DATA_DIR:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-extract -p /opt/car.lua "/data/$PBF_NAME"

echo "Partitioning..."
docker run --rm -t -v "$DATA_DIR:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-partition "/data/${PBF_NAME%.osm.pbf}.osrm"

echo "Customizing..."
docker run --rm -t -v "$DATA_DIR:/data" ghcr.io/project-osrm/osrm-backend \
  osrm-customize "/data/${PBF_NAME%.osm.pbf}.osrm"

echo ""
echo "Done. Update OSRM_DATA_FILE in .env if your filename differs, then run:"
echo "  docker compose up osrm"
