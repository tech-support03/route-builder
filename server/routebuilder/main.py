"""FastAPI app: routing, GPX export, saved locations, Garmin upload."""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import config, garmin, gpx, routing

app = FastAPI(title="route-builder")


class RouteRequest(BaseModel):
    points: list[tuple[float, float]] = Field(min_length=2, description="(lat, lon) waypoints")
    profile: str = "foot"
    preset: str = "default"


class RoundTripRequest(BaseModel):
    start: tuple[float, float]
    distance_m: float = Field(gt=0, le=100_000)
    seed: int = 0
    heading: float | None = None
    profile: str = "foot"
    preset: str = "default"


class OutAndBackRequest(BaseModel):
    start: tuple[float, float]
    turnaround: tuple[float, float]
    profile: str = "foot"
    preset: str = "default"


class ExportRequest(BaseModel):
    name: str
    points: list[tuple[float, float, float]] = Field(min_length=2, description="(lat, lon, ele)")
    distance_m: float = 0
    ascent_m: float = 0
    descent_m: float = 0
    upload_to_garmin: bool = False


class LoginRequest(BaseModel):
    email: str
    password: str
    mfa_code: str | None = None


class SaveRouteRequest(BaseModel):
    name: str
    data: dict


def _route_endpoint(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs).to_dict()
    except routing.RoutingError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/route")
def api_route(req: RouteRequest):
    return _route_endpoint(routing.route, req.points, profile=req.profile, preset=req.preset)


@app.post("/api/roundtrip")
def api_roundtrip(req: RoundTripRequest):
    return _route_endpoint(
        routing.round_trip,
        req.start,
        req.distance_m,
        seed=req.seed,
        heading=req.heading,
        profile=req.profile,
        preset=req.preset,
    )


@app.post("/api/outandback")
def api_outandback(req: OutAndBackRequest):
    return _route_endpoint(
        routing.out_and_back, req.start, req.turnaround, profile=req.profile, preset=req.preset
    )


@app.get("/api/presets")
def api_presets():
    return sorted(routing.PRESETS)


def _route_from_export(req: ExportRequest) -> routing.Route:
    route = routing.Route.__new__(routing.Route)
    route.points = [tuple(p) for p in req.points]
    route.distance_m = req.distance_m
    route.time_ms = 0
    route.ascent_m = req.ascent_m
    route.descent_m = req.descent_m
    return route


@app.post("/api/export")
def api_export(req: ExportRequest):
    """Save the route as GPX; optionally also upload it to Garmin Connect."""
    path = gpx.save_gpx(_route_from_export(req), req.name)
    result = {"gpx_path": str(path), "garmin": None, "garmin_error": None}
    if req.upload_to_garmin:
        try:
            result["garmin"] = garmin.upload_course(path, req.name)
        except garmin.GarminError as e:
            result["garmin_error"] = str(e)
    return result


@app.get("/api/gpx/{filename}")
def api_gpx_download(filename: str):
    path = (config.GPX_DIR / filename).resolve()
    if not path.is_file() or path.parent != config.GPX_DIR.resolve():
        raise HTTPException(status_code=404, detail="No such GPX")
    return FileResponse(path, media_type="application/gpx+xml", filename=path.name)


@app.get("/api/locations")
def api_locations():
    return config.load_locations()


@app.post("/api/locations/{name}")
def api_save_location(name: str, point: dict):
    locations = config.load_locations()
    locations[name] = {"lat": point["lat"], "lon": point["lon"]}
    config.save_locations(locations)
    return locations


@app.delete("/api/locations/{name}")
def api_delete_location(name: str):
    locations = config.load_locations()
    locations.pop(name, None)
    config.save_locations(locations)
    return locations


@app.get("/api/routes")
def api_list_routes():
    if not config.ROUTES_DIR.exists():
        return []
    return sorted(p.stem for p in config.ROUTES_DIR.glob("*.json"))


@app.get("/api/routes/{name}")
def api_get_route(name: str):
    path = config.ROUTES_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No such route")
    return json.loads(path.read_text())


@app.post("/api/routes")
def api_save_route(req: SaveRouteRequest):
    config.ROUTES_DIR.mkdir(parents=True, exist_ok=True)
    (config.ROUTES_DIR / f"{req.name}.json").write_text(json.dumps(req.data))
    return {"saved": req.name}


@app.get("/api/garmin/status")
def api_garmin_status():
    return garmin.status()


@app.post("/api/garmin/login")
def api_garmin_login(req: LoginRequest):
    try:
        provider = (lambda: req.mfa_code) if req.mfa_code else None
        garmin.login(req.email, req.password, mfa_code_provider=provider)
    except garmin.GarminError as e:
        raise HTTPException(status_code=401, detail=str(e))
    return garmin.status()


# Serve the built frontend when present (web/dist); vite dev proxies to us otherwise.
_dist = Path(__file__).resolve().parent.parent.parent / "web" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")


def serve():
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8990)
