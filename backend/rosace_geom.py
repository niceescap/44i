#!/usr/bin/env python3
"""Géométrie de la rosace {13/4} : 13 pointes + 39 croisements = 52 sites.

Les positions idéales sont la source de vérité. Un décalage minimal est
ensuite appliqué pour qu'aucune carte n'en recouvre une autre de plus
de 65 % de sa surface (AABB, dans l'espace du tapis).
"""

from __future__ import annotations

import math
from typing import Any

N = 13
K = 4
CX = 500.0
CY = 500.0
R = 392.0
MAX_COVER = 0.65
CARD_PX_W = 34.5
CARD_PX_H = 49.5


def _vertex(i: int) -> tuple[float, float]:
    a = -math.pi / 2 + (2 * math.pi * i) / N
    return math.cos(a), math.sin(a)


def _intersect(a, b, c, d) -> tuple[float, float] | None:
    den = (a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0])
    if abs(den) < 1e-12:
        return None
    t = ((a[0] - c[0]) * (c[1] - d[1]) - (a[1] - c[1]) * (c[0] - d[0])) / den
    u = ((a[0] - c[0]) * (a[1] - b[1]) - (a[1] - c[1]) * (a[0] - b[0])) / den
    if 1e-8 < t < 1 - 1e-8 and 1e-8 < u < 1 - 1e-8:
        return a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
    return None


def sites_unit() -> list[dict[str, Any]]:
    verts = [_vertex(i) for i in range(N)]
    tips = [
        {"id": i, "kind": "tip", "ux": verts[i][0], "uy": verts[i][1]}
        for i in range(N)
    ]
    crosses: list[dict[str, Any]] = []
    for i in range(N):
        for j in range(i + 1, N):
            ei = {i, (i + K) % N}
            ej = {j, (j + K) % N}
            if ei & ej:
                continue
            p = _intersect(verts[i], verts[(i + K) % N], verts[j], verts[(j + K) % N])
            if p:
                crosses.append({
                    "id": len(tips) + len(crosses),
                    "kind": "cross",
                    "ux": p[0],
                    "uy": p[1],
                    "edges": [i, j],
                })
    return tips + crosses


def to_canvas(sites: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for s in sites:
        r = math.hypot(s["ux"], s["uy"])
        item = dict(s)
        item.update({
            "x": CX + R * s["ux"],
            "y": CY + R * s["uy"],
            "radius": r,
            "angle": math.atan2(s["uy"], s["ux"]),
        })
        out.append(item)
    return out


def _overlap_area(a: dict, b: dict, w: float, h: float) -> float:
    ox = max(0.0, w - abs(a["x"] - b["x"]))
    oy = max(0.0, h - abs(a["y"] - b["y"]))
    return ox * oy


def _separation_scale(dx: float, dy: float, w: float, h: float, max_area: float) -> float:
    ax, ay = abs(dx), abs(dy)

    def ov(k: float) -> float:
        return max(0.0, w - k * ax) * max(0.0, h - k * ay)

    if ov(1.0) <= max_area:
        return 1.0
    lo, hi = 1.0, 1.0
    if ax > 1e-9:
        hi = max(hi, w / ax)
    if ay > 1e-9:
        hi = max(hi, h / ay)
    hi += 0.08
    for _ in range(22):
        mid = (lo + hi) / 2
        if ov(mid) > max_area:
            lo = mid
        else:
            hi = mid
    return hi


def separate_sites(
    geom: list[dict[str, Any]],
    w: float,
    h: float,
    max_cover: float = MAX_COVER,
) -> list[dict[str, Any]]:
    pts = [dict(s) for s in geom]
    n = len(pts)
    limit = max_cover * w * h
    for _ in range(80):
        worst = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                ov = _overlap_area(pts[i], pts[j], w, h)
                worst = max(worst, ov)
                if ov <= limit + 1e-4:
                    continue
                dx = pts[j]["x"] - pts[i]["x"]
                dy = pts[j]["y"] - pts[i]["y"]
                dist = math.hypot(dx, dy)
                if dist < 1e-6:
                    ang = pts[i].get("angle", 0.0) + (i + 1) * 0.31
                    dx, dy, dist = math.cos(ang), math.sin(ang), 1.0
                k = _separation_scale(dx, dy, w, h, limit)
                if k <= 1:
                    continue
                ux, uy = dx / dist, dy / dist
                push = (k - 1) * dist
                mi = 1.2 - 0.75 * min(pts[i].get("radius", 1.0), 1.0)
                mj = 1.2 - 0.75 * min(pts[j].get("radius", 1.0), 1.0)
                total = mi + mj
                pts[i]["x"] -= ux * push * (mi / total)
                pts[i]["y"] -= uy * push * (mi / total)
                pts[j]["x"] += ux * push * (mj / total)
                pts[j]["y"] += uy * push * (mj / total)
        if worst <= limit + 1e-4:
            break
    margin = max(w, h) * 0.55
    for p in pts:
        p["x"] = min(1000 - margin, max(margin, p["x"]))
        p["y"] = min(1000 - margin, max(margin, p["y"]))
    return pts


def layout(
    stage_w: float,
    stage_h: float,
    card_w: float = CARD_PX_W,
    card_h: float = CARD_PX_H,
) -> list[dict[str, Any]]:
    """52 sites : géométrie idéale + décalage anti-recouvrement > 65 %."""
    geom = to_canvas(sites_unit())
    sx = max(float(stage_w), 1.0)
    sy = max(float(stage_h), 1.0)
    w = card_w / sx * 1000.0
    h = card_h / sy * 1000.0
    return separate_sites(geom, w, h)


def public_sites(sites: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Positions envoyées au client — jamais le code de la carte."""
    return [
        {
            "id": s["id"],
            "kind": s["kind"],
            "x": round(s["x"], 3),
            "y": round(s["y"], 3),
        }
        for s in sites
    ]
