"""Garmin Connect integration via the unofficial API.

Auth uses python-garminconnect (mobile SSO flow with MFA support; the older
garth library's login is deprecated/broken). Course upload replicates the
two-step flow the Connect web UI uses, as reverse-engineered in
https://github.com/Taxuspt/garmin_mcp:

    1) POST /course-service/course/import   multipart GPX -> parsed geoPoints
    2) POST /course-service/course          JSON payload  -> saved course

This is the one deliberately-brittle module: Garmin can change these
endpoints without notice. Everything else works without it - every route is
saved as GPX for manual import at connect.garmin.com.
"""

import math
import os
from pathlib import Path

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectInvalidFileFormatError,
    GarminConnectTooManyRequestsError,
)
from requests import HTTPError, RequestException

from . import config

MANUAL_IMPORT_HINT = (
    "Import the GPX manually at connect.garmin.com -> "
    "Training & Planning -> Courses -> Import."
)

ACTIVITY_TYPE_IDS = {"running": 1, "trail_running": 6, "hiking": 3, "walking": 9}

_GARMIN_ERRORS = (
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectInvalidFileFormatError,
    GarminConnectTooManyRequestsError,
    HTTPError,
    RequestException,
)


class GarminError(Exception):
    pass


def _client() -> Garmin:
    garmin = Garmin()
    try:
        garmin.login(config.GARMIN_TOKENS)
    except Exception as e:
        raise GarminError("Not logged in to Garmin Connect. Run login first.") from e
    return garmin


def login(email: str, password: str, mfa_code_provider=None) -> None:
    """Authenticate and persist tokens (they auto-refresh afterwards)."""

    def prompt_mfa():
        if mfa_code_provider is None:
            raise GarminError("Garmin asked for an MFA code; retry with one provided.")
        code = mfa_code_provider()
        if not code:
            raise GarminError("Garmin asked for an MFA code; retry with one provided.")
        return code

    try:
        garmin = Garmin(email=email, password=password, prompt_mfa=prompt_mfa)
        garmin.login(config.GARMIN_TOKENS)  # logs in and persists tokens
    except _GARMIN_ERRORS as e:
        raise GarminError(f"Garmin login failed: {e}") from e


def status() -> dict:
    try:
        client = _client()
        return {"logged_in": True, "username": client.display_name or client.username}
    except (GarminError, *_GARMIN_ERRORS):
        return {"logged_in": False, "username": None}


def _post_json(client, path: str, **kwargs) -> dict:
    return client.post("connectapi", path, api=True, **kwargs)


def _haversine(p1: dict, p2: dict) -> float:
    lat1, lon1 = math.radians(p1["latitude"]), math.radians(p1["longitude"])
    lat2, lon2 = math.radians(p2["latitude"]), math.radians(p2["longitude"])
    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371000.0 * math.asin(math.sqrt(a))


def _build_payload(parsed: dict, name: str, activity_type_id: int) -> dict:
    geo_points = list(parsed.get("geoPoints") or [])
    if len(geo_points) < 2:
        raise GarminError("Garmin parsed fewer than 2 points from the GPX")

    total = 0.0
    for i, p in enumerate(geo_points):
        if i:
            total += _haversine(geo_points[i - 1], p)
        p["distance"] = total
        if p.get("elevation") is None:
            p["elevation"] = 0.0

    lats = [p["latitude"] for p in geo_points]
    lons = [p["longitude"] for p in geo_points]
    p0, pn = geo_points[0], geo_points[-1]
    dlon = math.radians(pn["longitude"] - p0["longitude"])
    la1, la2 = math.radians(p0["latitude"]), math.radians(pn["latitude"])
    bearing = (
        math.degrees(
            math.atan2(
                math.sin(dlon) * math.cos(la2),
                math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dlon),
            )
        )
        + 360
    ) % 360

    return {
        "courseName": name,
        "description": None,
        "openStreetMap": False,
        "matchedToSegments": False,
        "userProfilePk": None,
        "userGroupPk": None,
        "rulePK": 2,  # private
        "geoRoutePk": None,
        "sourceTypeId": 3,  # GPX
        "sourcePk": None,
        "distanceMeter": total,
        "elevationGainMeter": 0.0,  # server recomputes from its terrain DB
        "elevationLossMeter": 0.0,
        "startPoint": {
            "latitude": p0["latitude"],
            "longitude": p0["longitude"],
            "elevation": p0.get("elevation") or 0.0,
            "distance": None,
            "timestamp": None,
        },
        "coursePoints": [],
        "boundingBox": {
            "center": {
                "latitude": (min(lats) + max(lats)) / 2,
                "longitude": (min(lons) + max(lons)) / 2,
            },
            "lowerLeft": {"latitude": min(lats), "longitude": min(lons)},
            "upperRight": {"latitude": max(lats), "longitude": max(lons)},
            "lowerLeftLatIsSet": True,
            "lowerLeftLongIsSet": True,
            "upperRightLatIsSet": True,
            "upperRightLongIsSet": True,
        },
        "hasShareableEvent": False,
        "hasTurnDetectionDisabled": False,
        "activityTypePk": activity_type_id,
        "virtualPartnerId": None,
        "includeLaps": False,
        "elapsedSeconds": None,
        "speedMeterPerSecond": None,
        "courseLines": [
            {
                "courseId": None,
                "sortOrder": 1,
                "numberOfPoints": len(geo_points),
                "distanceInMeters": total,
                "bearing": bearing,
                "points": geo_points,
                "coordinateSystem": "WGS84",
                "originalCoordinateSystem": "WGS84",
            }
        ],
        "coordinateSystem": "WGS84",
        "targetCoordinateSystem": "WGS84",
        "originalCoordinateSystem": "WGS84",
        "consumer": None,
        "elevationSource": 3,
        "hasPaceBand": False,
        "hasPowerGuide": False,
        "favorite": False,
        "startNote": None,
        "finishNote": None,
        "cutoffDuration": None,
        "geoPoints": geo_points,
    }


def upload_course(gpx_path: Path, name: str, activity_type: str = "running") -> dict:
    """Upload a GPX file as a course; returns id/name/url of the saved course."""
    client = _client()
    type_id = ACTIVITY_TYPE_IDS.get(activity_type, ACTIVITY_TYPE_IDS["running"])
    try:
        parsed = _post_json(
            client.client,
            "/course-service/course/import",
            files={"file": (os.path.basename(gpx_path), Path(gpx_path).read_bytes(), "application/gpx+xml")},
        )
        payload = _build_payload(parsed, name, type_id)
        saved = _post_json(client.client, "/course-service/course", json=payload)
    except _GARMIN_ERRORS as e:
        raise GarminError(f"Garmin upload failed: {e}. {MANUAL_IMPORT_HINT}") from e
    if not saved.get("courseId"):
        raise GarminError(f"Garmin did not return a course id ({saved}). {MANUAL_IMPORT_HINT}")
    return {
        "course_id": saved["courseId"],
        "name": saved.get("courseName"),
        "distance_m": saved.get("distanceMeter"),
        "url": f"https://connect.garmin.com/modern/course/{saved['courseId']}",
    }
