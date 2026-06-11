# GraphHopper on the Raspberry Pi

Requirements: Pi 4 (4 GB), **64-bit** Raspberry Pi OS, ~10 GB free disk.

## Recommended flow: build the graph on the desktop, serve on the Pi

The NorCal extract (~700 MB `.pbf`) is at the edge of what a 4 GB Pi can
import. Serving needs far less RAM than importing, so build the graph on the
desktop and copy it over. This also makes future map expansions painless —
import the bigger extract on the desktop, rsync, restart.

On the desktop (from the repo root, same GraphHopper version as the Pi):

```sh
cd data
java -Xmx8g -jar graphhopper-web-11.0.jar import ../pi/config.yml
rsync -av graph-cache pi@<pi-host>:~/graphhopper/
```

On the Pi:

```sh
rsync -av pi/ pi@<pi-host>:~/route-builder-pi/   # copy this directory over first
ssh pi@<pi-host>
bash ~/route-builder-pi/setup.sh                  # installs Java, jar, systemd service
```

## Alternative: import on the Pi itself

```sh
bash ~/route-builder-pi/setup.sh --import
```

Stop memory-hungry services first; the import is given 2.7 GB of heap and a
NorCal-sized region takes a good while on a Pi.

## Expanding map coverage later

1. Pick a bigger extract (e.g. all of `california-latest.osm.pbf`) or merge
   several: `osmium merge norcal.pbf nevada.pbf -o combined.pbf`
2. Update `datareader.file` in `config.yml`, delete `graph-cache/`, re-import
   (on the desktop), rsync, `sudo systemctl restart graphhopper`.

The route-builder app never changes — it just talks to port 8989.

## Sanity check

Open `http://<pi-ip>:8989` — GraphHopper ships a built-in map UI. Pick the
`foot` profile and route between two points. Round-trip generation:

```
curl "http://<pi-ip>:8989/route?point=37.77,-122.45&profile=foot&algorithm=round_trip&round_trip.distance=8000&round_trip.seed=1&ch.disable=true"
```
