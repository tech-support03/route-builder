"""Garmin Connect integration via the unofficial API (garth).

This is the one deliberately-brittle module: course upload uses the same
internal course-service endpoint the Connect website uses, which Garmin can
change without notice. Everything else in the app works without it — every
route is saved as GPX for manual import at connect.garmin.com.
"""

from pathlib import Path

import garth
from garth.exc import GarthException

from . import config

MANUAL_IMPORT_HINT = (
    "Upload failed - import the GPX manually at connect.garmin.com -> "
    "Training & Planning -> Courses -> Import."
)


class GarminError(Exception):
    pass


def _client() -> garth.Client:
    client = garth.Client()
    try:
        client.load(config.GARTH_HOME)
    except (GarthException, FileNotFoundError) as e:
        raise GarminError("Not logged in to Garmin Connect. Run login first.") from e
    return client


def login(email: str, password: str, mfa_code_provider=None) -> None:
    """Authenticate and persist tokens to GARTH_HOME (auto-refresh afterwards)."""
    client = garth.Client()
    kwargs = {}
    if mfa_code_provider is not None:
        kwargs["prompt_mfa"] = mfa_code_provider
    try:
        client.login(email, password, **kwargs)
    except GarthException as e:
        raise GarminError(f"Garmin login failed: {e}") from e
    client.dump(config.GARTH_HOME)


def status() -> dict:
    try:
        client = _client()
        return {"logged_in": True, "username": client.username}
    except GarminError:
        return {"logged_in": False, "username": None}


def upload_course(gpx_path: Path, name: str) -> dict:
    """Upload a GPX file as a running course. Returns the created course info.

    NOTE: implemented in Phase 4 against the internal course-service endpoint;
    until then this raises with the manual-import fallback instructions.
    """
    raise GarminError(f"Auto-upload not wired up yet. {MANUAL_IMPORT_HINT}")
