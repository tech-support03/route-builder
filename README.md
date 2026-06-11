# route-builder

Personal running-route builder with one-click export to Garmin courses.

- **Web app**: interactive Leaflet map — click/drag waypoints, generate loops of a target
  distance, see elevation profiles, then send the route straight to Garmin Connect.
- **Routing**: self-hosted [GraphHopper](https://github.com/graphhopper/graphhopper)
  (foot/hike profiles, `round_trip` loop generation) running on a Raspberry Pi 4.
- **Garmin**: courses are uploaded via the unofficial Garmin Connect API
  ([garth](https://github.com/matin/garth) for auth); every route is also saved as GPX
  for manual import at connect.garmin.com → Training → Courses.
- **Claude Code skill**: conversational route generation ("give me a hilly 10k loop
  from home") reusing the same backend.

## Running it

```sh
# 1. routing engine (desktop dev instance; see pi/README.md for the Pi)
cd data && ./jre/bin/java -Xmx2g -jar graphhopper-web-11.0.jar server ../pi/config.yml &

# 2. backend + web UI  ->  http://localhost:8990
cd server && uv run routebuilder serve

# 3. (one-time) log in to Garmin so "Send to Garmin" works
cd server && uv run routebuilder login <email>
```

First-time desktop setup: `data/bootstrap.sh` downloads the JRE, GraphHopper,
and the NorCal OSM extract, then builds the routing graph.

CLI (what the Claude Code skill drives):

```sh
uv run routebuilder loop --from home --km 10 --preset hilly --upload
uv run routebuilder outback --from home --to 37.80,-122.42
uv run routebuilder location set home <lat,lon>
```

## Layout

| Path | What |
|---|---|
| `server/` | FastAPI backend: GraphHopper client, GPX writer, Garmin upload, CLI |
| `web/` | Vite + TypeScript + Leaflet frontend |
| `pi/` | GraphHopper config, setup script, and systemd unit for the Pi |
| `skill/` | Claude Code skill definition |
