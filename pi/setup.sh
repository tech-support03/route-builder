#!/usr/bin/env bash
# GraphHopper setup for Raspberry Pi 4 (64-bit OS required).
# Run on the Pi:  bash setup.sh [--import]
#
# Without --import it expects a graph-cache/ built elsewhere (recommended for
# NorCal-sized extracts; see pi/README.md for the desktop-import + rsync flow).
# With --import it downloads the NorCal extract and builds the graph on the Pi
# (needs ~2.7 GB free RAM; close other services first).
set -euo pipefail

GH_VERSION="11.0"
GH_JAR="graphhopper-web-${GH_VERSION}.jar"
PBF_URL="https://download.geofabrik.de/north-america/us/california/norcal-latest.osm.pbf"
INSTALL_DIR="${HOME}/graphhopper"

if [ "$(uname -m)" != "aarch64" ]; then
  echo "ERROR: 64-bit OS required (uname -m reports $(uname -m), expected aarch64)." >&2
  echo "Reinstall Raspberry Pi OS 64-bit before continuing." >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y openjdk-17-jre-headless

mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

if [ ! -f "${GH_JAR}" ]; then
  echo "Downloading GraphHopper ${GH_VERSION}..."
  curl -fLO "https://github.com/graphhopper/graphhopper/releases/download/${GH_VERSION}/${GH_JAR}"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "${SCRIPT_DIR}/config.yml" .

if [ "${1:-}" = "--import" ]; then
  if [ ! -f norcal-latest.osm.pbf ]; then
    echo "Downloading NorCal OSM extract (~700 MB)..."
    curl -fLO "${PBF_URL}"
  fi
  echo "Importing (this takes a while on a Pi; elevation tiles download on the fly)..."
  java -Xmx2700m -Xms2700m -jar "${GH_JAR}" import config.yml
elif [ ! -d graph-cache ]; then
  echo "No graph-cache/ found. Either:" >&2
  echo "  1. rsync a graph built on the desktop:  rsync -av desktop:~/Documents/route-builder/data/graph-cache ~/graphhopper/" >&2
  echo "  2. or re-run with --import to build it on the Pi" >&2
  exit 1
fi

echo "Installing systemd service..."
sudo cp "${SCRIPT_DIR}/graphhopper.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now graphhopper

echo "Done. Check: http://$(hostname -I | awk '{print $1}'):8989"
