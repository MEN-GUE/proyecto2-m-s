import math

import numpy as np
from numba import njit

# indices del vector de parametros
TAU, A, B, AW, BW, MASS, DT, TMAX, VCAP, SIGMA, SAMPLE, SPACING, MARGIN, SERVE_R, GIVE_UP = range(15)
CELL = 2.0


@njit(cache=True)
def _nearest(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = min(max(t, 0.0), 1.0)
    qx, qy = x1 + t * dx, y1 + t * dy
    return qx, qy, math.hypot(px - qx, py - qy)


@njit(cache=True)
def _crosses(ax, ay, bx, by, cx, cy, dx, dy):
    d1 = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    d2 = (bx - ax) * (dy - ay) - (by - ay) * (dx - ax)
    d3 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx)
    d4 = (dx - cx) * (by - cy) - (dy - cy) * (bx - cx)
    return d1 * d2 < 0 and d3 * d4 < 0


@njit(cache=True)
def simulate(pos0, v0, rad, line, dur, walls, gates, fdist, fdir, line_field, sp, qdir,
             nav0, dens0, walk, prm, frames):
    n, nl, nw, ng = pos0.shape[0], sp.shape[0], walls.shape[0], gates.shape[0]
    dt, tau, m = prm[DT], prm[TAU], prm[MASS]
    pos, vel = pos0.copy(), np.zeros((n, 2))
    state = np.where(line >= 0, 0, 2)
    qpos = np.full(n, -1)
    t_exit = np.full(n, np.nan)
    gate_of = np.full(n, -1)
    served = np.zeros(n, np.bool_)
    unserved = 0
    qids = np.full((max(nl, 1), n), -1)
    head = np.zeros(max(nl, 1), np.int64)
    tail = np.zeros(max(nl, 1), np.int64)
    busy = np.full(max(nl, 1), -1.0)

    gx0, gy0, gh = nav0[0], nav0[1], nav0[2]
    nfx, nfy = fdist.shape[1], fdist.shape[2]
    ncx, ncy = int(nfx * gh / CELL) + 1, int(nfy * gh / CELL) + 1
    start = np.zeros(ncx * ncy + 1, np.int64)
    fill = np.zeros(ncx * ncy, np.int64)
    members = np.empty(n, np.int64)
    cell = np.full(n, -1)
    wstart = np.zeros(ncx * ncy + 1, np.int64)
    wlist = np.empty(ncx * ncy * nw, np.int64)
    reach = CELL + 0.75 * CELL
    for c in range(ncx * ncy):
        cxm, cym = gx0 + (c // ncy + 0.5) * CELL, gy0 + (c % ncy + 0.5) * CELL
        wstart[c + 1] = wstart[c]
        for w in range(nw):
            if _nearest(cxm, cym, walls[w, 0], walls[w, 1], walls[w, 2], walls[w, 3])[2] < reach:
                wlist[wstart[c + 1]] = w
                wstart[c + 1] += 1

    dx0, dy0, dh = dens0[0], dens0[1], dens0[2]
    dnx, dny = walk.shape
    dens, dmap = np.zeros((dnx, dny)), np.zeros((dnx, dny))
    sig2 = 2 * prm[SIGMA] ** 2
    norm = 1 / (math.pi * sig2)
    kr = int(3 * prm[SIGMA] / dh) + 1
    wy = np.zeros(2 * kr + 1)
    every = int(prm[SAMPLE] / dt + 0.5)
    nsamp = int(prm[TMAX] / prm[SAMPLE]) + 3
    dser = np.zeros(nsamp)
    nin, nout = np.zeros(nsamp, np.int64), np.zeros(nsamp, np.int64)

    e, spd, force = np.zeros((n, 2)), np.zeros(n), np.zeros((n, 2))
    t, step, k, out, crossings = 0.0, 0, 0, 0, 0
    while True:
        done = out == n or t >= prm[TMAX]
        if (step % every == 0 or done) and k < nsamp:
            dens[:] = 0.0
            for i in range(n):
                if state[i] == 3:
                    continue
                ci, cj = int((pos[i, 0] - dx0) / dh), int((pos[i, 1] - dy0) / dh)
                b0, b1 = max(cj - kr, 0), min(cj + kr + 1, dny)
                for b in range(b0, b1):
                    wy[b - b0] = norm * math.exp(-(dy0 + (b + 0.5) * dh - pos[i, 1]) ** 2 / sig2)
                for a in range(max(ci - kr, 0), min(ci + kr + 1, dnx)):
                    wx = math.exp(-(dx0 + (a + 0.5) * dh - pos[i, 0]) ** 2 / sig2)
                    for b in range(b0, b1):
                        dens[a, b] += wx * wy[b - b0]
            peak = 0.0
            for a in range(dnx):
                for b in range(dny):
                    if walk[a, b]:
                        peak = max(peak, dens[a, b])
                        dmap[a, b] = max(dmap[a, b], dens[a, b])
            dser[k], nout[k], nin[k] = peak, out, n - out
            if k < frames.shape[0]:
                frames[k] = pos
            k += 1
        if done:
            break

        # colas: fin de servicio y llegada del primero de la fila al punto de atencion
        for l in range(nl):
            if busy[l] >= 0 and t >= busy[l]:
                i = qids[l, head[l]]
                if state[i] == 1:
                    state[i] = 2
                served[i] = True
                head[l] += 1
                busy[l] = -1.0
            while busy[l] < 0 and head[l] < tail[l] and state[qids[l, head[l]]] == 3:
                head[l] += 1
            if busy[l] < 0 and head[l] < tail[l]:
                i = qids[l, head[l]]
                if math.hypot(pos[i, 0] - sp[l, 0], pos[i, 1] - sp[l, 1]) < prm[SERVE_R]:
                    busy[l] = t + dur[i]

        # direccion deseada
        for i in range(n):
            s = state[i]
            if s == 3:
                continue
            ci = min(max(int((pos[i, 0] - gx0) / gh), 0), nfx - 1)
            cj = min(max(int((pos[i, 1] - gy0) / gh), 0), nfy - 1)
            ex, ey, sv = 0.0, 0.0, v0[i]
            if s == 0 and t > prm[GIVE_UP]:
                state[i] = s = 2
            if s == 2:
                ex, ey = fdir[0, ci, cj, 0], fdir[0, ci, cj, 1]
            else:
                l = line[i]
                rank = tail[l] - head[l] if s == 0 else qpos[i] - head[l]
                tx = sp[l, 0] + rank * prm[SPACING] * qdir[l, 0] - pos[i, 0]
                ty = sp[l, 1] + rank * prm[SPACING] * qdir[l, 1] - pos[i, 1]
                d = math.hypot(tx, ty)
                f = line_field[l]
                if s == 0 and d < 1.0:
                    qids[l, tail[l]] = i
                    qpos[i] = tail[l]
                    tail[l] += 1
                    state[i] = s = 1
                if s == 0 and d > 2.5 and fdist[f, ci, cj] > 0.5:
                    ex, ey = fdir[f, ci, cj, 0], fdir[f, ci, cj, 1]
                elif d > 1e-6:
                    ex, ey = tx / d, ty / d
                    if s == 1:
                        sv = v0[i] * min(1.0, d / 0.5)
            e[i, 0], e[i, 1], spd[i] = ex, ey, sv

        # grilla de vecinos
        start[:] = 0
        for i in range(n):
            if state[i] == 3:
                cell[i] = -1
                continue
            cx = min(max(int((pos[i, 0] - gx0) / CELL), 0), ncx - 1)
            cy = min(max(int((pos[i, 1] - gy0) / CELL), 0), ncy - 1)
            cell[i] = cx * ncy + cy
            start[cell[i] + 1] += 1
        for c in range(ncx * ncy):
            start[c + 1] += start[c]
        fill[:] = 0
        for i in range(n):
            if cell[i] >= 0:
                members[start[cell[i]] + fill[cell[i]]] = i
                fill[cell[i]] += 1

        # fuerzas de repulsion
        for i in range(n):
            if cell[i] < 0:
                continue
            fx, fy = 0.0, 0.0
            cx, cy = cell[i] // ncy, cell[i] % ncy
            for a in range(max(cx - 1, 0), min(cx + 2, ncx)):
                for b in range(max(cy - 1, 0), min(cy + 2, ncy)):
                    c = a * ncy + b
                    for q in range(start[c], start[c + 1]):
                        j = members[q]
                        if j == i:
                            continue
                        rx, ry = pos[i, 0] - pos[j, 0], pos[i, 1] - pos[j, 1]
                        d = math.hypot(rx, ry)
                        if 1e-9 < d < CELL:
                            f = prm[A] * math.exp((rad[i] + rad[j] - d) / prm[B]) / d
                            fx += f * rx
                            fy += f * ry
            for q in range(wstart[cell[i]], wstart[cell[i] + 1]):
                w = wlist[q]
                qx, qy, d = _nearest(pos[i, 0], pos[i, 1], walls[w, 0], walls[w, 1], walls[w, 2], walls[w, 3])
                if 1e-9 < d < CELL:
                    f = prm[AW] * math.exp((rad[i] - d) / prm[BW]) / d
                    fx += f * (pos[i, 0] - qx)
                    fy += f * (pos[i, 1] - qy)
            force[i, 0], force[i, 1] = fx, fy

        # integracion semi implicita, choques con muros y salida
        for i in range(n):
            if cell[i] < 0:
                continue
            for c in range(2):
                vel[i, c] = (vel[i, c] + dt * (spd[i] * e[i, c] / tau + force[i, c] / m)) / (1 + dt / tau)
            sv = math.hypot(vel[i, 0], vel[i, 1])
            vmax = prm[VCAP] * v0[i]
            if sv > vmax:
                vel[i, 0] *= vmax / sv
                vel[i, 1] *= vmax / sv
            nx_, ny_ = pos[i, 0] + vel[i, 0] * dt, pos[i, 1] + vel[i, 1] * dt
            for q in range(wstart[cell[i]], wstart[cell[i] + 1]):
                w = wlist[q]
                if _crosses(pos[i, 0], pos[i, 1], nx_, ny_, walls[w, 0], walls[w, 1], walls[w, 2], walls[w, 3]):
                    crossings += 1
                qx, qy, d = _nearest(nx_, ny_, walls[w, 0], walls[w, 1], walls[w, 2], walls[w, 3])
                if 1e-9 < d < rad[i]:
                    ux, uy = (nx_ - qx) / d, (ny_ - qy) / d
                    nx_, ny_ = qx + ux * rad[i], qy + uy * rad[i]
                    vn = vel[i, 0] * ux + vel[i, 1] * uy
                    if vn < 0:
                        vel[i, 0] -= vn * ux
                        vel[i, 1] -= vn * uy
            pos[i, 0], pos[i, 1] = nx_, ny_
            for g in range(ng):
                ax, ay = gates[g, 0], gates[g, 1]
                lx, ly = gates[g, 2] - ax, gates[g, 3] - ay
                s = ((nx_ - ax) * lx + (ny_ - ay) * ly) / (lx * lx + ly * ly)
                u = (nx_ - ax) * gates[g, 4] + (ny_ - ay) * gates[g, 5]
                if u > prm[MARGIN] and -0.1 <= s <= 1.1:
                    if line[i] >= 0 and not served[i]:
                        unserved += 1
                    state[i] = 3
                    t_exit[i] = t + dt
                    gate_of[i] = g
                    out += 1
                    pos[i, 0], pos[i, 1] = -1e3, -1e3
                    break
        t += dt
        step += 1
    return t_exit, gate_of, unserved, dser[:k], nin[:k], nout[:k], dmap, crossings, t
