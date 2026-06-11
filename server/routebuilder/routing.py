"""GraphHopper client: point-to-point routing and round-trip loop generation."""

from typing import Any

import httpx

from . import config

# Custom models merge with the profile's base model server-side. Custom model
# priority can only penalize (multiply_by <= 1), so "prefer trails" means
# "penalize roads" and "hilly" means "penalize flat".
PRESETS: dict[str, dict[str, Any] | None] = {
    "default": None,
    "trails": {
        "priority": [
            {"if": "road_class == PRIMARY || road_class == SECONDARY", "multiply_by": "0.2"},
            {"if": "road_class == TERTIARY || road_class == RESIDENTIAL", "multiply_by": "0.6"},
        ]
    },
    "flat": {
        "priority": [
            {"if": "average_slope >= 4 || average_slope <= -4", "multiply_by": "0.3"},
            {"if": "average_slope >= 2 || average_slope <= -2", "multiply_by": "0.7"},
        ]
    },
    "hilly": {
        "priority": [
            {"if": "average_slope < 2 && average_slope > -2", "multiply_by": "0.5"},
        ]
    },
}


class RoutingError(Exception):
    pass


class Route:
    """A computed route: coordinates are (lat, lon, ele) tuples."""

    def __init__(self, path: dict[str, Any]):
        # GraphHopper returns [lon, lat, ele]
        self.points: list[tuple[float, float, float]] = [
            (p[1], p[0], p[2] if len(p) > 2 else 0.0)
            for p in path["points"]["coordinates"]
        ]
        self.distance_m: float = path["distance"]
        self.time_ms: int = path["time"]
        self.ascent_m: float = path.get("ascend", 0.0)
        self.descent_m: float = path.get("descend", 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": [[round(lat, 6), round(lon, 6), round(ele, 1)] for lat, lon, ele in self.points],
            "distance_m": round(self.distance_m, 1),
            "time_ms": self.time_ms,
            "ascent_m": round(self.ascent_m, 1),
            "descent_m": round(self.descent_m, 1),
        }


def _request(body: dict[str, Any]) -> Route:
    body.setdefault("elevation", True)
    body.setdefault("points_encoded", False)
    body.setdefault("instructions", False)
    body.setdefault("ch.disable", True)
    try:
        resp = httpx.post(f"{config.GRAPHHOPPER_URL}/route", json=body, timeout=30)
    except httpx.HTTPError as e:
        raise RoutingError(f"GraphHopper unreachable at {config.GRAPHHOPPER_URL}: {e}") from e
    if resp.status_code != 200:
        try:
            msg = resp.json().get("message", resp.text)
        except ValueError:
            msg = resp.text
        raise RoutingError(f"GraphHopper error: {msg}")
    return Route(resp.json()["paths"][0])


def _apply_preset(body: dict[str, Any], preset: str) -> None:
    if preset not in PRESETS:
        raise RoutingError(f"Unknown preset {preset!r}; choose from {sorted(PRESETS)}")
    model = PRESETS[preset]
    if model:
        body["custom_model"] = model


def route(points: list[tuple[float, float]], profile: str = "foot", preset: str = "default") -> Route:
    """Snap a route through the given (lat, lon) waypoints."""
    if len(points) < 2:
        raise RoutingError("Need at least 2 points")
    body: dict[str, Any] = {
        "points": [[lon, lat] for lat, lon in points],
        "profile": profile,
    }
    _apply_preset(body, preset)
    return _request(body)


def round_trip(
    start: tuple[float, float],
    distance_m: float,
    seed: int = 0,
    heading: float | None = None,
    profile: str = "foot",
    preset: str = "default",
) -> Route:
    """Generate a loop of approximately distance_m starting and ending at start."""
    body: dict[str, Any] = {
        "points": [[start[1], start[0]]],
        "profile": profile,
        "algorithm": "round_trip",
        "round_trip.distance": int(distance_m),
        "round_trip.seed": seed,
    }
    if heading is not None:
        body["heading"] = [heading]
    _apply_preset(body, preset)
    return _request(body)


def out_and_back(
    start: tuple[float, float],
    turnaround: tuple[float, float],
    profile: str = "foot",
    preset: str = "default",
) -> Route:
    """Route to a turnaround point and mirror the path back to the start."""
    out = route([start, turnaround], profile=profile, preset=preset)
    mirrored = Route.__new__(Route)
    mirrored.points = out.points + out.points[-2::-1]
    mirrored.distance_m = out.distance_m * 2
    mirrored.time_ms = out.time_ms * 2
    mirrored.ascent_m = out.ascent_m + out.descent_m
    mirrored.descent_m = out.descent_m + out.ascent_m
    return mirrored
