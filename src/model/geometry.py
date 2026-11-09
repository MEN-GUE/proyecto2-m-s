import json
import math

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from . import params as P
from .data import OSM_FILE, fetch_osm

LAT0, LON0 = 14.6115, -90.4825   # origen de la proyeccion local
WINDOW = (0.0, -14.5)            # esquina suroeste de la ventana en ese marco
R_EARTH = 6371000.0


def to_local(lat, lon):
    k = math.pi / 180 * R_EARTH
    return ((lon - LON0) * k * math.cos(math.radians(LAT0)) - WINDOW[0],
            (lat - LAT0) * k - WINDOW[1])


def load_lot():
    fetch_osm()
    way = json.loads(OSM_FILE.read_text())["elements"][0]
    return Polygon([to_local(p["lat"], p["lon"]) for p in way["geometry"]])


def _segments(geom):
    lines = geom.geoms if hasattr(geom, "geoms") else [geom]
    out = []
    for line in lines:
        c = list(line.coords)
        out += [(*c[i], *c[i + 1]) for i in range(len(c) - 1)]
    return np.array(out)


class Venue:
    def __init__(self):
        self.lot = load_lot()
        self.domain = self.lot.intersection(box(0, 0, P.WIDTH, P.HEIGHT))
        self.gates = np.array([self._gate(x) for x in P.GATE_X])
        cut = unary_union([LineString([g[:2], g[2:4]]).buffer(1e-6) for g in self.gates])
        self.walls = _segments(self.domain.exterior.difference(cut))

    def _gate(self, x):
        hit = self.domain.exterior.intersection(LineString([(x, -1), (x, P.HEIGHT + 1)]))
        pts = [hit] if hit.geom_type == "Point" else list(hit.geoms)
        c = np.array(min(pts, key=lambda p: p.y).coords[0])
        seg = _segments(self.domain.exterior)
        d = [LineString([s[:2], s[2:]]).distance(LineString([c, c])) for s in seg]
        s = seg[int(np.argmin(d))]
        t = (s[2:] - s[:2]) / np.linalg.norm(s[2:] - s[:2])
        n = np.array([t[1], -t[0]])
        if self.domain.contains(Point(c + 0.5 * n)):
            n = -n
        h = P.GATE_WIDTH / 2
        return np.array([*(c - h * t), *(c + h * t), *n])


def bar_box(cx, cy):
    return box(cx - P.BAR_W / 2, cy - P.BAR_H / 2, cx + P.BAR_W / 2, cy + P.BAR_H / 2)


def fence_line(mx, my, th):
    d = 0.5 * P.FENCE_LEN * np.array([math.cos(th), math.sin(th)])
    return LineString([(mx - d[0], my - d[1]), (mx + d[0], my + d[1])])


def baseline_layout(venue):
    bars = []
    for cy in (11.0, 19.5, 28.0, 36.5):
        strip = venue.domain.exterior.intersection(box(-1, cy - P.BAR_H / 2, 20, cy + P.BAR_H / 2))
        bars.append((strip.bounds[2] + 0.2 + P.BAR_W / 2, cy))
    return {"bars": bars, "fences": []}


def layout_segments(venue, layout):
    segs = [venue.walls]
    for cx, cy in layout["bars"]:
        segs.append(_segments(bar_box(cx, cy).exterior))
    for f in layout["fences"]:
        segs.append(_segments(fence_line(*f)))
    return np.vstack(segs)


def service_points(layout):
    pts = [(cx + P.BAR_W / 2 + 0.45, cy + o) for cx, cy in layout["bars"] for o in P.SERVER_OFFSETS]
    return np.array(pts)


if __name__ == "__main__":
    v = Venue()
    print(f"Lote OSM: {v.lot.area:.0f} m2, dominio: {v.domain.area:.0f} m2")
    print("Portones:", np.round(v.gates[:, :4], 2).tolist())
    print("Base:", baseline_layout(v))
