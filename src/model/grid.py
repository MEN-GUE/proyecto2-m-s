import heapq

import numpy as np
from numba import njit

from . import params as P

H = 0.25
PAD = 2.0
POCKET = 1.5


def inside_polygon(x, y, poly):
    inside = np.zeros(x.shape, bool)
    xj, yj = poly[-1]
    for xi, yi in poly:
        if yi != yj:
            inside ^= ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi) + xi)
        xj, yj = xi, yi
    return inside


def seg_distance(x, y, segs):
    d = np.full(x.shape, np.inf)
    for x1, y1, x2, y2 in segs:
        dx, dy = x2 - x1, y2 - y1
        t = np.clip(((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy), 0, 1)
        d = np.minimum(d, np.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return d


def box_distance(x, y, cx, cy, hw, hh):
    return np.hypot(np.maximum(np.abs(x - cx) - hw, 0), np.maximum(np.abs(y - cy) - hh, 0))


@njit(cache=True)
def dijkstra(cost, sources, h):
    nx, ny = cost.shape
    dist = np.full((nx, ny), np.inf)
    heap = [(0.0, 0, 0)]
    heap.pop()
    for i in range(nx):
        for j in range(ny):
            if sources[i, j] and cost[i, j] < np.inf:
                dist[i, j] = 0.0
                heap.append((0.0, i, j))
    heapq.heapify(heap)
    while len(heap) > 0:
        d, i, j = heapq.heappop(heap)
        if d > dist[i, j]:
            continue
        for di in range(-1, 2):
            for dj in range(-1, 2):
                a, b = i + di, j + dj
                if (di == 0 and dj == 0) or a < 0 or b < 0 or a >= nx or b >= ny or cost[a, b] == np.inf:
                    continue
                diag = di != 0 and dj != 0
                if diag and (cost[a, j] == np.inf or cost[i, b] == np.inf):
                    continue
                nd = d + h * cost[a, b] * (1.4142135623730951 if diag else 1.0)
                if nd < dist[a, b]:
                    dist[a, b] = nd
                    heapq.heappush(heap, (nd, a, b))
    return dist


class Grid:
    def __init__(self, venue):
        bx0, by0, bx1, by1 = venue.domain.bounds
        self.x0, self.y0 = bx0 - PAD, by0 - PAD
        xs = self.x0 + H * (np.arange(int((bx1 - bx0 + 2 * PAD) / H)) + 0.5)
        ys = self.y0 + H * (np.arange(int((by1 - by0 + 2 * PAD) / H)) + 0.5)
        self.x, self.y = np.meshgrid(xs, ys, indexing="ij")
        self.domain = inside_polygon(self.x, self.y, np.array(venue.domain.exterior.coords))
        self.wall_d = seg_distance(self.x, self.y, venue.walls)
        self.pocket = np.zeros_like(self.domain)
        self.source = np.zeros_like(self.domain)
        for g in venue.gates:
            a, b, n = g[:2], g[2:4], g[4:]
            t = (b - a) / np.linalg.norm(b - a)
            s = (self.x - a[0]) * t[0] + (self.y - a[1]) * t[1]
            u = (self.x - a[0]) * n[0] + (self.y - a[1]) * n[1]
            span = (s >= 0) & (s <= P.GATE_WIDTH)
            self.pocket |= span & (u > 0) & (u <= POCKET)
            self.source |= span & (u > 1.0) & (u <= POCKET)
        self.gate_d = np.min([np.hypot(self.x - (g[0] + g[2]) / 2, self.y - (g[1] + g[3]) / 2)
                              for g in venue.gates], axis=0)
        empty = self.free([], P.MIN_GAP / 2)
        self.dead = empty & self.domain & np.isinf(self.distance_to_exit(empty))

    def obstacle_distances(self, layout):
        d = [box_distance(self.x, self.y, cx, cy, P.BAR_W / 2, P.BAR_H / 2) for cx, cy in layout["bars"]]
        for mx, my, th in layout["fences"]:
            h = 0.5 * P.FENCE_LEN * np.array([np.cos(th), np.sin(th)])
            d.append(seg_distance(self.x, self.y, [(mx - h[0], my - h[1], mx + h[0], my + h[1])]))
        return d

    def free(self, obstacle_d, clearance):
        ok = (self.domain | self.pocket) & (self.wall_d >= clearance)
        for d in obstacle_d:
            ok &= d >= clearance
        return ok

    def distance_to_exit(self, free):
        return dijkstra(np.where(free, 1.0, np.inf), self.source, H)
