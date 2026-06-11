---
name: route-builder
description: Generate running routes (loops, out-and-backs) and send them to a Garmin watch as courses. Use when the user asks for a running route, a loop of some distance, a jog/run suggestion, or to send a course to their Garmin.
---

# route-builder

Generates snapped running routes via a local GraphHopper instance and exports
them as GPX + Garmin Connect courses. Project lives at
`~/Documents/route-builder`.

## How to run

All commands run from `~/Documents/route-builder/server` with
`PATH="$HOME/.local/bin:$PATH"` (for uv):

```sh
uv run routebuilder loop --from home --km 10 --name "Morning 10k"
uv run routebuilder loop --at 37.77,-122.45 --km 8 --preset hilly --seed 2 --upload
uv run routebuilder outback --from home --to 37.80,-122.42 --name "Bridge out-and-back"
uv run routebuilder location list
uv run routebuilder location set work 37.79,-122.40
uv run routebuilder location set home 450 Jersey St, San Francisco, CA   # addresses work too (geocoded via Nominatim)
uv run routebuilder status          # Garmin login state
```

## Mapping user requests to flags

- "10k", "5 miles" → `--km 10` / `--km 8` (convert miles: ×1.609)
- "hilly" → `--preset hilly`; "flat" → `--preset flat`; "trails/scenic" → `--preset trails`
- "trail run" → also `--profile hike`
- "from home/work/<saved place>" → `--from <name>`; explicit coords → `--at lat,lon`
- "different one / shuffle" → increment `--seed` and rerun
- "send it to my watch / Garmin" → add `--upload`
- A direction ("head north") → `--heading 0` (N=0, E=90, S=180, W=270)
- Always pass a descriptive `--name` (it becomes the course name on the watch)

Round-trip distance is approximate (±25% is normal). If the result is far off,
retry with a different `--seed` or scale the requested `--km`.

## Output

The CLI prints distance, ascent/descent, and the GPX path. Report those to the
user. On `--upload` it prints the Garmin course URL. For visual editing,
mention the web UI: start it with `uv run routebuilder serve` (if not already
running) and open http://localhost:8990.

## Troubleshooting

- **"GraphHopper unreachable"**: the routing engine isn't running. Local dev
  instance: `cd ~/Documents/route-builder/data && ./jre/bin/java -Xmx2g -jar
  graphhopper-web-11.0.jar server ../pi/config.yml &` (takes ~30 s to start).
  If a Pi instance exists instead, set `GRAPHHOPPER_URL=http://<pi-ip>:8989`.
- **"Not logged in to Garmin"**: the user must run
  `uv run routebuilder login <email>` themselves (interactive password + MFA).
  Never ask for or handle their password.
- **Point outside map bounds**: the graph only covers Northern California;
  coordinates elsewhere will fail until a bigger extract is imported.
- **Upload fails**: the GPX is still on disk — tell the user to import it at
  connect.garmin.com → Training & Planning → Courses → Import.
