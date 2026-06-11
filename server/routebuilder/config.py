"""Configuration: GraphHopper URL, output paths, saved locations."""

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

GRAPHHOPPER_URL = os.environ.get("GRAPHHOPPER_URL", "http://localhost:8989")

GPX_DIR = Path(os.environ.get("ROUTEBUILDER_GPX_DIR", REPO_ROOT / "gpx"))
DATA_DIR = Path(os.environ.get("ROUTEBUILDER_DATA_DIR", REPO_ROOT / "userdata"))
LOCATIONS_FILE = DATA_DIR / "locations.json"
ROUTES_DIR = DATA_DIR / "routes"

GARMIN_TOKENS = os.environ.get("GARMIN_TOKENS", os.path.expanduser("~/.garminconnect"))


def load_locations() -> dict[str, dict]:
    """Named saved locations, e.g. {"home": {"lat": ..., "lon": ...}}."""
    if LOCATIONS_FILE.exists():
        return json.loads(LOCATIONS_FILE.read_text())
    return {}


def save_locations(locations: dict[str, dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOCATIONS_FILE.write_text(json.dumps(locations, indent=2))
