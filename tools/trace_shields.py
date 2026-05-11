"""Trace shield silhouettes from the raster source into polygons.

For each shield we trace the boundary of every coloured region (transparent
outside, black, opaque-white) using Moore-neighbour contour tracing.
The polygons are stored in unit-square coordinates (0..1) so the renderer
can scale them to any size without quality loss — true vector behaviour.

The final output is a Python module containing a SHIELD_POLYGONS dict.

Layered render order (largest area first):
  - white_shield: outer-black-silhouette, then inner-white-interior.
  - black_shield: outer-black-silhouette, then inner-white-annulus,
                  then inner-black-core.
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SHIELD_PNGS = {
    "white_shield": "/Users/ag/Code/python-chess-ai-yt/.claude/worktrees/sweet-morse/assets/images/imgs-80px/white_shield.png",
    "black_shield": "/Users/ag/Code/python-chess-ai-yt/.claude/worktrees/sweet-morse/assets/images/imgs-80px/black_shield.png",
}

OUTPUT_MODULE = "/Users/ag/Code/python-chess-ai-yt/.claude/worktrees/sweet-morse/src/shield_polygons.py"

# Classify any RGB channel above this threshold as "white", below as "black",
# considered only for opaque pixels.
WHITE_THRESHOLD = 128

# Minimum polygon area (in pixels) — filters tiny stray components like
# anti-aliasing residue or JPEG-compression artifacts that aren't part
# of the intended shield geometry. 500 keeps the inner black core
# (~1500 px) but rejects the ~100-px noise blobs.
MIN_POLY_AREA = 500

# Douglas–Peucker simplification tolerance, in pixels. Higher = fewer vertices,
# more aggressive simplification. 0.6 keeps the silhouette very faithful while
# typically reducing several hundred boundary pixels to ~60-100 vertices.
SIMPLIFY_EPSILON = 0.6


# ---------------------------------------------------------------------------
# Connected components (4-neighbour) on a boolean mask
# ---------------------------------------------------------------------------

def label_components(mask):
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    n = 0
    for y in range(h):
        for x in range(w):
            if mask[y, x] and labels[y, x] == 0:
                n += 1
                stack = [(y, x)]
                while stack:
                    cy, cx = stack.pop()
                    if cy < 0 or cy >= h or cx < 0 or cx >= w:
                        continue
                    if labels[cy, cx] != 0 or not mask[cy, cx]:
                        continue
                    labels[cy, cx] = n
                    stack.append((cy - 1, cx))
                    stack.append((cy + 1, cx))
                    stack.append((cy, cx - 1))
                    stack.append((cy, cx + 1))
    return labels, n


# ---------------------------------------------------------------------------
# Moore-neighbour contour tracing on a boolean mask
# ---------------------------------------------------------------------------
#
# Direction index convention (y increases downward, clockwise from East):
#   0 = E, 1 = SE, 2 = S, 3 = SW, 4 = W, 5 = NW, 6 = N, 7 = NE
#
# Walking around a region clockwise: when we arrive at a pixel from direction
# `came_from`, we start the search at `came_from + 1` (mod 8) and rotate
# clockwise, picking the first neighbour that is inside the region.

_MOORE_DELTAS = [
    (0, 1),   # E
    (1, 1),   # SE
    (1, 0),   # S
    (1, -1),  # SW
    (0, -1),  # W
    (-1, -1), # NW
    (-1, 0),  # N
    (-1, 1),  # NE
]


def trace_contour(mask, start_y, start_x):
    """Trace the closed boundary of the connected region containing
    (start_y, start_x). Returns an ordered list of (y, x) pixel coordinates."""
    h, w = mask.shape
    contour = []
    visited_with_dir = set()  # (y, x, came_from) for termination check.

    current_y, current_x = start_y, start_x
    came_from = 4  # pretend we arrived from the West, so we first look East-ish.

    while True:
        contour.append((current_y, current_x))
        key = (current_y, current_x, came_from)
        if key in visited_with_dir:
            break  # we've revisited the same state — done.
        visited_with_dir.add(key)

        # Search clockwise starting from the direction immediately after `came_from`.
        found = False
        for i in range(1, 9):
            d = (came_from + i) % 8
            dy, dx = _MOORE_DELTAS[d]
            ny, nx = current_y + dy, current_x + dx
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx]:
                # Move to this pixel; we arrived from direction (d + 4) mod 8.
                current_y, current_x = ny, nx
                came_from = (d + 4) % 8
                found = True
                break

        if not found:
            break  # isolated pixel, no boundary continuation.

        if len(contour) > 200_000:
            print("WARNING: contour exceeded 200k vertices, breaking")
            break

    return contour


def find_topleft_pixel(mask):
    """Return (y, x) of the lexicographically smallest True pixel."""
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return None
    idx = int(np.argmin(ys * (mask.shape[1] + 1) + xs))
    return (int(ys[idx]), int(xs[idx]))


# ---------------------------------------------------------------------------
# Douglas–Peucker polygon simplification
# ---------------------------------------------------------------------------

def _perpendicular_distance(p, a, b):
    """Distance from point p to the line segment from a to b."""
    if a == b:
        return ((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2) ** 0.5
    ax, ay = a
    bx, by = b
    px, py = p
    dx = bx - ax
    dy = by - ay
    # Project p onto the line, clamp to segment, distance to projection.
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5


def douglas_peucker(points, epsilon):
    """Simplify a polyline using the Douglas–Peucker algorithm.
    points: list of (y, x) or (x, y). Returns subset of points."""
    if len(points) < 3:
        return points[:]
    # Iterative implementation to avoid deep recursion on long contours.
    keep = [False] * len(points)
    keep[0] = True
    keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue
        a = points[start]
        b = points[end]
        max_dist = 0.0
        max_idx = start
        for i in range(start + 1, end):
            d = _perpendicular_distance(points[i], a, b)
            if d > max_dist:
                max_dist = d
                max_idx = i
        if max_dist > epsilon:
            keep[max_idx] = True
            stack.append((start, max_idx))
            stack.append((max_idx, end))
    return [p for i, p in enumerate(points) if keep[i]]


# ---------------------------------------------------------------------------
# Per-shield processing
# ---------------------------------------------------------------------------

def classify_pixels(rgba_arr):
    """Map each pixel to a class: 0 = transparent, 1 = white, 2 = black.
    The shield interior we previously made opaque-white maps to class 1.
    The shield outline / body / core maps to class 2.
    """
    alpha = rgba_arr[..., 3]
    r = rgba_arr[..., 0]
    g = rgba_arr[..., 1]
    b = rgba_arr[..., 2]
    is_opaque = alpha > 0
    is_bright = (r > WHITE_THRESHOLD) & (g > WHITE_THRESHOLD) & (b > WHITE_THRESHOLD)
    out = np.zeros_like(alpha, dtype=np.int8)
    out[is_opaque & ~is_bright] = 2  # black
    out[is_opaque & is_bright] = 1   # white
    return out


def polygon_enclosed_area(points):
    """Shoelace formula. Returns the area enclosed by a closed polygon
    (irrespective of orientation). For a ring-shaped pixel component
    (e.g. the outer outline of an outline-only shield), the traced
    boundary is the OUTER perimeter, so this returns the area of the
    full shape — not just the ring's pixel count. That's the value we
    want for correct nesting order."""
    n = len(points)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2


def extract_polygons(rgba):
    """Return a list of polygon layers ordered correctly for layered
    rendering: OUTERMOST first, INNERMOST last. "Outermost" is measured
    by polygon-enclosed area (shoelace) rather than component pixel count,
    because a ring-shaped component's outer perimeter encloses the whole
    shield even though the component itself is thin.

    Each layer is a dict with 'color' (hex), 'points' (normalised to
    [0,1] over image size), and 'enclosed_area' (debug-keep)."""
    arr = np.array(rgba)
    h, w = arr.shape[:2]
    cls = classify_pixels(arr)

    layers = []  # list of (enclosed_area, color, polygon_pixel_points, comp_area)
    for class_value, color in [(2, "#000000"), (1, "#ffffff")]:
        mask = cls == class_value
        component_labels, n = label_components(mask)
        for lbl in range(1, n + 1):
            comp_mask = component_labels == lbl
            comp_area = int(comp_mask.sum())
            if comp_area < MIN_POLY_AREA:
                continue
            start = find_topleft_pixel(comp_mask)
            if start is None:
                continue
            raw_contour = trace_contour(comp_mask, *start)
            xy = [(x, y) for (y, x) in raw_contour]
            simplified = douglas_peucker(xy, SIMPLIFY_EPSILON)
            enclosed = polygon_enclosed_area(simplified)
            layers.append((enclosed, color, simplified, comp_area))

    # Sort by ENCLOSED polygon area (descending): outermost shape first.
    # This is what we need for layered rendering — the outer silhouette
    # fills the whole shield first, then inner shapes overlay on top.
    layers.sort(key=lambda c: -c[0])

    normalised = []
    for enclosed, color, pixel_points, comp_area in layers:
        norm = [(x / (w - 1), y / (h - 1)) for (x, y) in pixel_points]
        normalised.append({
            "color": color,
            "points": norm,
            "enclosed_area": int(enclosed),
            "component_area": comp_area,
        })

    return normalised


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def main():
    all_polys = {}
    for name, path in SHIELD_PNGS.items():
        img = Image.open(path).convert("RGBA")
        polys = extract_polygons(img)
        all_polys[name] = polys
        print(f"{name}: {len(polys)} polygon(s)")
        for i, p in enumerate(polys):
            print(f"  layer {i}: color={p['color']} "
                  f"enclosed={p['enclosed_area']} component={p['component_area']} "
                  f"vertices={len(p['points'])}")

    # Emit a clean Python module so the renderer can import it directly
    # without parsing JSON at runtime.
    lines = [
        '"""Vector shield polygons for v2 knight invulnerability indicator.',
        "",
        "Auto-generated by /tmp/trace_shields.py from the raster source PNGs.",
        "Polygons are in unit-square coordinates (0..1) so they can be scaled",
        "to any size at render time. Each shield's polygon list is rendered",
        "in order: index 0 is the base layer (largest area), subsequent",
        "entries paint on top.",
        '"""',
        "",
        "SHIELD_POLYGONS = {",
    ]
    for name, polys in all_polys.items():
        lines.append(f"    {name!r}: [")
        for p in polys:
            lines.append(f"        {{")
            lines.append(f"            'color': {p['color']!r},")
            pts = p["points"]
            lines.append(f"            'points': [")
            for (x, y) in pts:
                lines.append(f"                ({x:.6f}, {y:.6f}),")
            lines.append(f"            ],")
            lines.append(f"        }},")
        lines.append(f"    ],")
    lines.append("}")
    lines.append("")

    out_path = Path(OUTPUT_MODULE)
    out_path.write_text("\n".join(lines))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
