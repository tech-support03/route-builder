// Elevation profile chart on a <canvas>, with hover synced to a map marker.

const R = 6371000;
function haversine(a, b) {
  const dLat = ((b[0] - a[0]) * Math.PI) / 180;
  const dLon = ((b[1] - a[1]) * Math.PI) / 180;
  const la1 = (a[0] * Math.PI) / 180, la2 = (b[0] * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export class ElevationChart {
  constructor(container, canvas, map) {
    this.container = container;
    this.canvas = canvas;
    this.map = map;
    this.points = null; // [lat, lon, ele]
    this.dists = null;  // cumulative meters
    this.hoverMarker = L.circleMarker([0, 0], { radius: 6, color: "#f59e0b", fillOpacity: 0.9 });
    canvas.addEventListener("mousemove", (e) => this.onHover(e));
    canvas.addEventListener("mouseleave", () => this.hoverMarker.remove());
    new ResizeObserver(() => this.draw(this.hoverX)).observe(canvas);
  }

  setRoute(points) {
    this.points = points;
    if (!points || points.length < 2) {
      this.container.hidden = true;
      this.hoverMarker.remove();
      return;
    }
    this.dists = [0];
    for (let i = 1; i < points.length; i++) {
      this.dists.push(this.dists[i - 1] + haversine(points[i - 1], points[i]));
    }
    this.container.hidden = false;
    this.hoverX = null;
    this.draw();
  }

  draw(hoverX = null) {
    if (!this.points) return;
    const c = this.canvas, ctx = c.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    c.width = c.clientWidth * dpr;
    c.height = c.clientHeight * dpr;
    ctx.scale(dpr, dpr);
    const W = c.clientWidth, H = c.clientHeight;
    const padL = 36, padB = 16, padT = 8;
    ctx.clearRect(0, 0, W, H);

    const eles = this.points.map((p) => p[2]);
    let min = Math.min(...eles), max = Math.max(...eles);
    if (max - min < 10) { max += 5; min -= 5; }
    const total = this.dists[this.dists.length - 1];
    const x = (d) => padL + (d / total) * (W - padL - 4);
    const y = (e) => padT + (1 - (e - min) / (max - min)) * (H - padT - padB);

    // filled profile
    ctx.beginPath();
    ctx.moveTo(x(0), y(eles[0]));
    for (let i = 1; i < this.points.length; i++) ctx.lineTo(x(this.dists[i]), y(eles[i]));
    ctx.strokeStyle = "#60a5fa";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.lineTo(x(total), H - padB);
    ctx.lineTo(x(0), H - padB);
    ctx.closePath();
    ctx.fillStyle = "rgba(96, 165, 250, 0.25)";
    ctx.fill();

    // axes labels
    ctx.fillStyle = "#9aa3b5";
    ctx.font = "10px system-ui";
    ctx.fillText(`${Math.round(max)} m`, 2, padT + 8);
    ctx.fillText(`${Math.round(min)} m`, 2, H - padB - 2);
    const kmStep = total > 15000 ? 5 : total > 6000 ? 2 : 1;
    for (let km = kmStep; km * 1000 < total; km += kmStep) {
      ctx.fillText(`${km}`, x(km * 1000) - 3, H - 4);
    }

    if (hoverX !== null) {
      ctx.strokeStyle = "#f59e0b";
      ctx.beginPath();
      ctx.moveTo(hoverX, padT);
      ctx.lineTo(hoverX, H - padB);
      ctx.stroke();
    }
    this.hoverX = hoverX;
  }

  onHover(e) {
    if (!this.points) return;
    const rect = this.canvas.getBoundingClientRect();
    const W = rect.width, padL = 36;
    const total = this.dists[this.dists.length - 1];
    const d = Math.max(0, Math.min(total, ((e.clientX - rect.left - padL) / (W - padL - 4)) * total));
    // binary search nearest point
    let lo = 0, hi = this.dists.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (this.dists[mid] < d) lo = mid + 1; else hi = mid;
    }
    const p = this.points[lo];
    this.hoverMarker.setLatLng([p[0], p[1]]).addTo(this.map);
    this.draw(e.clientX - rect.left);
  }
}
