"""CLI for the Claude Code skill (and humans): generate routes from arguments.

Examples:
    routebuilder loop --from home --km 10 --preset hilly --name "Tuesday 10k"
    routebuilder loop --at 37.77,-122.45 --km 8 --seed 3 --upload
    routebuilder outback --from home --to 37.80,-122.42 --name "Bridge out-and-back"
    routebuilder location set home 37.77,-122.45
    routebuilder login you@example.com   (prompts for password/MFA)
    routebuilder serve
"""

import argparse
import getpass
import json
import sys

from . import config, garmin, gpx, routing


def _parse_point(s: str) -> tuple[float, float]:
    lat, lon = s.split(",")
    return (float(lat), float(lon))


def _resolve_start(args) -> tuple[float, float]:
    if args.at:
        return _parse_point(args.at)
    locations = config.load_locations()
    name = getattr(args, "from_loc", None) or "home"
    if name not in locations:
        sys.exit(
            f"Unknown location {name!r}. Saved locations: {sorted(locations) or 'none'}. "
            f"Add one with: routebuilder location set {name} <lat,lon>"
        )
    return (locations[name]["lat"], locations[name]["lon"])


def _finish(route: routing.Route, name: str, upload: bool) -> None:
    path = gpx.save_gpx(route, name)
    print(f"Route: {route.distance_m / 1000:.2f} km, +{route.ascent_m:.0f} m / -{route.descent_m:.0f} m")
    print(f"GPX:   {path}")
    if upload:
        try:
            info = garmin.upload_course(path, name)
            print(f"Garmin: uploaded ({json.dumps(info)})")
        except garmin.GarminError as e:
            print(f"Garmin: {e}", file=sys.stderr)
            sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(prog="routebuilder", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--at", help="start as lat,lon")
        p.add_argument("--from", dest="from_loc", help="start as a saved location name (default: home)")
        p.add_argument("--name", default="route-builder course", help="route/course name")
        p.add_argument("--preset", default="default", choices=sorted(routing.PRESETS))
        p.add_argument("--profile", default="foot", choices=["foot", "hike"])
        p.add_argument("--upload", action="store_true", help="upload to Garmin Connect")

    p = sub.add_parser("loop", help="generate a round-trip loop")
    add_common(p)
    p.add_argument("--km", type=float, required=True, help="target distance in km")
    p.add_argument("--seed", type=int, default=0, help="change for a different loop")
    p.add_argument("--heading", type=float, help="initial direction in degrees (0=N, 90=E)")

    p = sub.add_parser("outback", help="out-and-back to a turnaround point")
    add_common(p)
    p.add_argument("--to", dest="to", required=True, help="turnaround as lat,lon or saved location")

    p = sub.add_parser("location", help="manage saved locations")
    p.add_argument("action", choices=["list", "set", "delete"])
    p.add_argument("name", nargs="?")
    p.add_argument("point", nargs="*", help="lat,lon or a street address (for set)")

    p = sub.add_parser("login", help="log in to Garmin Connect (tokens persist)")
    p.add_argument("email")

    sub.add_parser("status", help="Garmin login status")
    sub.add_parser("serve", help="run the web app backend")

    args = parser.parse_args()

    if args.cmd == "loop":
        start = _resolve_start(args)
        route = routing.round_trip(
            start, args.km * 1000, seed=args.seed, heading=args.heading,
            profile=args.profile, preset=args.preset,
        )
        _finish(route, args.name, args.upload)
    elif args.cmd == "outback":
        start = _resolve_start(args)
        locations = config.load_locations()
        if args.to in locations:
            turnaround = (locations[args.to]["lat"], locations[args.to]["lon"])
        else:
            turnaround = _parse_point(args.to)
        route = routing.out_and_back(start, turnaround, profile=args.profile, preset=args.preset)
        _finish(route, args.name, args.upload)
    elif args.cmd == "location":
        locations = config.load_locations()
        if args.action == "list":
            print(json.dumps(locations, indent=2))
        elif args.action == "set":
            if not args.name or not args.point:
                sys.exit('Usage: routebuilder location set <name> <lat,lon | street address>')
            query = " ".join(args.point)
            try:
                lat, lon = _parse_point(query)
                label = None
            except ValueError:
                from . import geocode

                try:
                    match = geocode.geocode_one(query)
                except geocode.GeocodeError as e:
                    sys.exit(str(e))
                lat, lon, label = match["lat"], match["lon"], match["label"]
            locations[args.name] = {"lat": lat, "lon": lon}
            config.save_locations(locations)
            print(f"Saved {args.name} = {lat},{lon}" + (f"  ({label})" if label else ""))
        elif args.action == "delete":
            locations.pop(args.name, None)
            config.save_locations(locations)
            print(f"Deleted {args.name}")
    elif args.cmd == "login":
        password = getpass.getpass("Garmin password: ")
        garmin.login(args.email, password, mfa_code_provider=lambda: input("MFA code: "))
        print(json.dumps(garmin.status()))
    elif args.cmd == "status":
        print(json.dumps(garmin.status()))
    elif args.cmd == "serve":
        from .main import serve

        serve()


if __name__ == "__main__":
    main()
