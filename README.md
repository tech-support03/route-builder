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

## Layout

| Path | What |
|---|---|
| `server/` | FastAPI backend: GraphHopper client, GPX writer, Garmin upload, CLI |
| `web/` | Vite + TypeScript + Leaflet frontend |
| `pi/` | GraphHopper config, setup script, and systemd unit for the Pi |
| `skill/` | Claude Code skill definition |
