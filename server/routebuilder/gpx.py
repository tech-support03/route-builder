"""GPX 1.1 writer. Garmin Connect's course importer reads a single <trk>."""

import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from . import config
from .routing import Route

GPX_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="route-builder"
     xmlns="http://www.topografix.com/GPX/1/1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
  <metadata>
    <name>{name}</name>
    <time>{time}</time>
  </metadata>
  <trk>
    <name>{name}</name>
    <type>running</type>
    <trkseg>
{points}
    </trkseg>
  </trk>
</gpx>
"""


def to_gpx(route: Route, name: str) -> str:
    points = "\n".join(
        f'      <trkpt lat="{lat:.6f}" lon="{lon:.6f}"><ele>{ele:.1f}</ele></trkpt>'
        for lat, lon, ele in route.points
    )
    return GPX_TEMPLATE.format(
        name=escape(name),
        time=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        points=points,
    )


def save_gpx(route: Route, name: str) -> Path:
    config.GPX_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "route"
    path = config.GPX_DIR / f"{slug}.gpx"
    # Avoid silently clobbering an earlier route with the same name
    counter = 2
    while path.exists():
        path = config.GPX_DIR / f"{slug}-{counter}.gpx"
        counter += 1
    path.write_text(to_gpx(route, name))
    return path
