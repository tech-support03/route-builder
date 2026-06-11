import { api } from "./api.js";
import { ElevationChart } from "./elevation.js";

const $ = (id) => document.getElementById(id);
const statusEl = $("status");

function setStatus(msg, cls = "") {
  statusEl.textContent = msg;
  statusEl.className = cls;
}

// ---- map ----
const map = L.map("map").setView([37.7749, -122.4194], 13);
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  maxZoom: 19,
}).addTo(map);

const chart = new ElevationChart($("elevation"), $("elev-canvas"), map);

// ---- state ----
let mode = "manual";
let waypoints = [];        // L.Marker list (manual: many; loop: 1; outback: 2)
let routeLine = null;
let kmMarkers = [];
let currentRoute = null;   // last response from the backend
let seed = 0;
let history = [];          // for undo: snapshots of waypoint latlngs

const HINTS = {
  manual: "Click the map to add waypoints. Drag to move, right-click to remove.",
  loop: "Click the map to set the loop start, then tune distance/direction.",
  outback: "Click start, then the turnaround point. The route mirrors back.",
};

// ---- waypoint helpers ----
function addWaypoint(latlng) {
  const marker = L.marker(latlng, { draggable: true }).addTo(map);
  marker.on("dragend", () => regenerate());
  marker.on("contextmenu", () => {
    if (mode !== "manual") return;
    pushHistory();
    waypoints = waypoints.filter((m) => m !== marker);
    marker.remove();
    regenerate();
  });
  waypoints.push(marker);
  return marker;
}

function clearWaypoints() {
  waypoints.forEach((m) => m.remove());
  waypoints = [];
}

function pushHistory() {
  history.push(waypoints.map((m) => m.getLatLng()));
  if (history.length > 50) history.shift();
}

function restoreWaypoints(latlngs) {
  clearWaypoints();
  latlngs.forEach((ll) => addWaypoint(ll));
}

// ---- rendering ----
function renderRoute(route, fit = false) {
  currentRoute = route;
  if (routeLine) routeLine.remove();
  kmMarkers.forEach((m) => m.remove());
  kmMarkers = [];

  const latlngs = route.points.map((p) => [p[0], p[1]]);
  routeLine = L.polyline(latlngs, { color: "#2563eb", weight: 4, opacity: 0.85 }).addTo(map);
  if (fit) map.fitBounds(routeLine.getBounds(), { padding: [30, 30] });

  // km markers
  let next = 1000, acc = 0, n = 1;
  for (let i = 1; i < latlngs.length; i++) {
    acc += map.distance(latlngs[i - 1], latlngs[i]);
    if (acc >= next) {
      kmMarkers.push(
        L.marker(latlngs[i], {
          interactive: false,
          icon: L.divIcon({ className: "", html: `<div class="km-marker">${n}</div>`, iconSize: [18, 18] }),
        }).addTo(map)
      );
      n += 1;
      next += 1000;
    }
  }

  $("stats").hidden = false;
  $("stat-dist").textContent = (route.distance_m / 1000).toFixed(2);
  $("stat-up").textContent = Math.round(route.ascent_m);
  $("stat-down").textContent = Math.round(route.descent_m);
  chart.setRoute(route.points);
  ["download", "send-garmin", "save-route"].forEach((id) => ($(id).disabled = false));
}

function clearRoute() {
  if (routeLine) routeLine.remove();
  routeLine = null;
  kmMarkers.forEach((m) => m.remove());
  kmMarkers = [];
  currentRoute = null;
  $("stats").hidden = true;
  chart.setRoute(null);
  ["download", "send-garmin", "save-route"].forEach((id) => ($(id).disabled = true));
}

// ---- route generation ----
async function regenerate(fit = false) {
  const profile = $("profile").value;
  const preset = $("preset").value;
  try {
    if (mode === "manual") {
      if (waypoints.length < 2) { clearRoute(); return; }
      setStatus("Routing…");
      const pts = waypoints.map((m) => [m.getLatLng().lat, m.getLatLng().lng]);
      renderRoute(await api.route(pts, profile, preset), fit);
    } else if (mode === "loop") {
      if (waypoints.length < 1) return;
      setStatus("Generating loop…");
      const ll = waypoints[0].getLatLng();
      const heading = $("heading").value === "" ? null : Number($("heading").value);
      const km = Number($("km").value);
      renderRoute(await api.roundTrip([ll.lat, ll.lng], km * 1000, seed, heading, profile, preset), fit);
    } else if (mode === "outback") {
      if (waypoints.length < 2) { clearRoute(); return; }
      setStatus("Routing…");
      const [a, b] = waypoints.map((m) => m.getLatLng());
      renderRoute(await api.outAndBack([a.lat, a.lng], [b.lat, b.lng], profile, preset), fit);
    }
    setStatus("");
  } catch (e) {
    setStatus(e.message, "error");
  }
}

map.on("click", (e) => {
  if (mode === "manual") {
    pushHistory();
    addWaypoint(e.latlng);
    regenerate();
  } else if (mode === "loop") {
    pushHistory();
    clearWaypoints();
    addWaypoint(e.latlng);
    regenerate(true);
  } else if (mode === "outback") {
    pushHistory();
    if (waypoints.length >= 2) clearWaypoints();
    addWaypoint(e.latlng);
    regenerate();
  }
});

// ---- panel wiring ----
$("modes").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-mode]");
  if (!btn) return;
  mode = btn.dataset.mode;
  document.querySelectorAll("#modes button").forEach((b) => b.classList.toggle("active", b === btn));
  $("loop-controls").hidden = mode !== "loop";
  $("mode-hint").textContent = HINTS[mode];
  clearWaypoints();
  clearRoute();
  history = [];
});

$("km").addEventListener("input", () => ($("km-label").textContent = Number($("km").value).toFixed(1)));
$("km").addEventListener("change", () => regenerate(true));
$("heading").addEventListener("change", () => regenerate(true));
$("shuffle").addEventListener("click", () => { seed += 1; regenerate(true); });
$("preset").addEventListener("change", () => regenerate());
$("profile").addEventListener("change", () => regenerate());

$("undo").addEventListener("click", () => {
  if (!history.length) return;
  restoreWaypoints(history.pop());
  regenerate();
});

$("clear").addEventListener("click", () => {
  pushHistory();
  clearWaypoints();
  clearRoute();
});

$("locate").addEventListener("click", () => {
  setStatus("Locating…");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const ll = [pos.coords.latitude, pos.coords.longitude];
      map.setView(ll, 15);
      setStatus("");
      if (mode === "loop") {
        clearWaypoints();
        addWaypoint(L.latLng(ll[0], ll[1]));
        regenerate(true);
      }
    },
    (err) => setStatus(`Geolocation failed: ${err.message}`, "error"),
    { enableHighAccuracy: true, timeout: 10000 }
  );
});

// saved locations
async function refreshLocations() {
  const locations = await api.locations();
  const sel = $("locations");
  sel.length = 1;
  for (const name of Object.keys(locations).sort()) {
    const o = document.createElement("option");
    o.value = name;
    o.textContent = name;
    sel.appendChild(o);
  }
  sel.dataset.locations = JSON.stringify(locations);
}

$("locations").addEventListener("change", () => {
  const sel = $("locations");
  if (!sel.value) return;
  const loc = JSON.parse(sel.dataset.locations)[sel.value];
  map.setView([loc.lat, loc.lon], 15);
  if (mode === "loop" || mode === "outback" || mode === "manual") {
    if (mode === "loop") clearWaypoints();
    addWaypoint(L.latLng(loc.lat, loc.lon));
    regenerate(mode === "loop");
  }
  sel.value = "";
});

$("loc-save").addEventListener("click", async () => {
  const name = $("loc-name").value.trim();
  if (!name) { setStatus("Give the place a name first", "error"); return; }
  const ll = waypoints.length ? waypoints[0].getLatLng() : map.getCenter();
  await api.saveLocation(name, ll.lat, ll.lng);
  $("loc-name").value = "";
  await refreshLocations();
  setStatus(`Saved place "${name}"`, "ok");
});

// export / garmin
function exportPayload(upload) {
  return {
    name: $("route-name").value.trim() || "My route",
    points: currentRoute.points,
    distance_m: currentRoute.distance_m,
    ascent_m: currentRoute.ascent_m,
    descent_m: currentRoute.descent_m,
    upload_to_garmin: upload,
  };
}

$("download").addEventListener("click", async () => {
  try {
    const res = await api.export(exportPayload(false));
    const filename = res.gpx_path.split("/").pop();
    window.location.href = `/api/gpx/${encodeURIComponent(filename)}`;
    setStatus(`GPX saved: ${res.gpx_path}`, "ok");
  } catch (e) { setStatus(e.message, "error"); }
});

$("send-garmin").addEventListener("click", async () => {
  setStatus("Uploading to Garmin…");
  try {
    const res = await api.export(exportPayload(true));
    if (res.garmin_error) {
      setStatus(`${res.garmin_error}\nGPX kept at ${res.gpx_path}`, "error");
    } else {
      setStatus("Course uploaded to Garmin Connect ✔", "ok");
    }
  } catch (e) { setStatus(e.message, "error"); }
});

// save / load routes
$("save-route").addEventListener("click", async () => {
  const name = $("route-name").value.trim() || "My route";
  await api.saveRoute(name, {
    mode,
    waypoints: waypoints.map((m) => [m.getLatLng().lat, m.getLatLng().lng]),
    route: currentRoute,
    params: { km: $("km").value, heading: $("heading").value, seed, preset: $("preset").value, profile: $("profile").value },
  });
  await refreshSavedRoutes();
  setStatus(`Route "${name}" saved`, "ok");
});

async function refreshSavedRoutes() {
  const names = await api.listRoutes();
  const sel = $("load-route");
  sel.length = 1;
  names.forEach((n) => {
    const o = document.createElement("option");
    o.value = n;
    o.textContent = n;
    sel.appendChild(o);
  });
}

$("load-route").addEventListener("change", async () => {
  const name = $("load-route").value;
  if (!name) return;
  const data = await api.getRoute(name);
  mode = data.mode;
  document.querySelectorAll("#modes button").forEach((b) => b.classList.toggle("active", b.dataset.mode === mode));
  $("loop-controls").hidden = mode !== "loop";
  $("km").value = data.params.km;
  $("km-label").textContent = Number(data.params.km).toFixed(1);
  $("heading").value = data.params.heading;
  seed = data.params.seed || 0;
  $("preset").value = data.params.preset;
  $("profile").value = data.params.profile;
  $("route-name").value = name;
  restoreWaypoints(data.waypoints.map(([lat, lon]) => L.latLng(lat, lon)));
  if (data.route) renderRoute(data.route, true);
  $("load-route").value = "";
});

// garmin status / login
async function refreshGarmin() {
  try {
    const s = await api.garminStatus();
    if (s.logged_in) {
      $("garmin-status").textContent = `Garmin: logged in as ${s.username}`;
      $("garmin-login").hidden = true;
    } else {
      $("garmin-status").textContent = "Garmin: not logged in";
      $("garmin-login").hidden = false;
    }
  } catch {
    $("garmin-status").textContent = "Garmin: status unavailable";
  }
}

$("garmin-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  setStatus("Logging in to Garmin…");
  try {
    await api.garminLogin($("g-email").value, $("g-pass").value, $("g-mfa").value.trim());
    $("g-pass").value = "";
    setStatus("Garmin login OK", "ok");
    await refreshGarmin();
  } catch (err) { setStatus(err.message, "error"); }
});

// ---- init ----
(async function init() {
  const presets = await api.presets();
  for (const p of presets) {
    const o = document.createElement("option");
    o.value = p;
    o.textContent = p;
    $("preset").appendChild(o);
  }
  $("preset").value = "default";
  await Promise.all([refreshLocations(), refreshSavedRoutes(), refreshGarmin()]);
})();
