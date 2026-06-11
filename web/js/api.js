async function call(method, path, body) {
  const resp = await fetch(path, {
    method,
    headers: body ? { "content-type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!resp.ok) {
    let detail;
    try { detail = (await resp.json()).detail; } catch { detail = resp.statusText; }
    throw new Error(detail);
  }
  return resp.json();
}

export const api = {
  route: (points, profile, preset) => call("POST", "/api/route", { points, profile, preset }),
  roundTrip: (start, distance_m, seed, heading, profile, preset) =>
    call("POST", "/api/roundtrip", { start, distance_m, seed, heading, profile, preset }),
  outAndBack: (start, turnaround, profile, preset) =>
    call("POST", "/api/outandback", { start, turnaround, profile, preset }),
  presets: () => call("GET", "/api/presets"),
  export: (payload) => call("POST", "/api/export", payload),
  locations: () => call("GET", "/api/locations"),
  saveLocation: (name, lat, lon) => call("POST", `/api/locations/${encodeURIComponent(name)}`, { lat, lon }),
  listRoutes: () => call("GET", "/api/routes"),
  getRoute: (name) => call("GET", `/api/routes/${encodeURIComponent(name)}`),
  saveRoute: (name, data) => call("POST", "/api/routes", { name, data }),
  garminStatus: () => call("GET", "/api/garmin/status"),
  garminLogin: (email, password, mfa_code) =>
    call("POST", "/api/garmin/login", { email, password, mfa_code: mfa_code || null }),
};
