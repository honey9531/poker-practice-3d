"""Triangle meshes for the 3D poker table (pure Python, no Qt).

The table is a stadium (a rectangle with fully rounded ends) lying in the
x/z plane with the felt surface at ``y = 0``; ``+z`` points towards the human
player and ``+y`` up. One unit is roughly one centimetre.

Each part is generated separately so QML can give it its own material:

* ``felt``  - flat playing surface
* ``trim``  - narrow wooden racetrack around the felt
* ``rail``  - padded leather cushion
* ``apron`` - the table's outer side, below the rail
* ``line``  - the betting line painted on the felt

The rim parts are a 2D profile (radial offset from the felt edge, height)
swept along the stadium outline. Vertices are interleaved as
``x, y, z, nx, ny, nz, u, v`` (see :data:`STRIDE`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

FELT_RADIUS = 45.5  # radius of the felt's rounded ends
STRAIGHT_HALF = 61.5  # half-length of the straight sides (centres of the ends)
TRIM_WIDTH = 3.0
RAIL_WIDTH = 11.0
RAIL_HEIGHT = 6.5
TRIM_HEIGHT = 0.6
APRON_DEPTH = 12.0
OUTER_RADIUS = FELT_RADIUS + TRIM_WIDTH + RAIL_WIDTH
OUTER_WIDTH = 2 * (STRAIGHT_HALF + OUTER_RADIUS)
OUTER_DEPTH = 2 * OUTER_RADIUS

FELT_TILE = 24.0  # felt texture repeat, in units
ARC_SEGMENTS = 48  # per rounded end
FLOATS_PER_VERTEX = 8
STRIDE = FLOATS_PER_VERTEX * 4  # bytes per vertex (float32)

BETTING_LINE_INSET = 9.6  # distance of the betting line inside the felt edge
PARTS = ("felt", "trim", "rail", "apron", "line")


@dataclass(frozen=True, slots=True)
class Mesh:
    vertices: list[float]  # interleaved, FLOATS_PER_VERTEX per vertex
    indices: list[int]  # triangles

    @property
    def vertex_count(self) -> int:
        return len(self.vertices) // FLOATS_PER_VERTEX

    def positions(self) -> list[tuple[float, float, float]]:
        v, n = self.vertices, FLOATS_PER_VERTEX
        return [(v[i], v[i + 1], v[i + 2]) for i in range(0, len(v), n)]

    def normals(self) -> list[tuple[float, float, float]]:
        v, n = self.vertices, FLOATS_PER_VERTEX
        return [(v[i + 3], v[i + 4], v[i + 5]) for i in range(0, len(v), n)]

    def bounds(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        points = self.positions()
        return (
            tuple(min(p[k] for p in points) for k in range(3)),  # type: ignore[return-value]
            tuple(max(p[k] for p in points) for k in range(3)),
        )


@dataclass(frozen=True, slots=True)
class OutlinePoint:
    """A point on the stadium's spine with the outward direction there.

    The outline at radius ``r`` is ``(cx + nx * r, cz + nz * r)``.
    """

    cx: float
    cz: float
    nx: float
    nz: float


def stadium_outline(segments: int = ARC_SEGMENTS) -> list[OutlinePoint]:
    """Closed outline: right end (far to near), then left end (near to far).

    The straight sides are the implicit edges between the two ends.
    """
    points = []
    for centre, start in ((STRAIGHT_HALF, -90.0), (-STRAIGHT_HALF, 90.0)):
        for i in range(segments + 1):
            angle = math.radians(start + 180.0 * i / segments)
            points.append(OutlinePoint(centre, 0.0, math.cos(angle), math.sin(angle)))
    return points


def _profile_normals(profile: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Smooth 2D normals (radial, up) for a profile polyline.

    The profile runs from the inside of the table outwards, so turning each
    segment's direction a quarter turn anticlockwise points away from the solid.
    """
    segment_normals = []
    for (r0, y0), (r1, y1) in zip(profile, profile[1:]):
        dr, dy = r1 - r0, y1 - y0
        length = math.hypot(dr, dy)
        segment_normals.append((-dy / length, dr / length))
    normals = []
    for i in range(len(profile)):
        around = segment_normals[max(0, i - 1): i + 1]
        nr = sum(n[0] for n in around)
        ny = sum(n[1] for n in around)
        length = math.hypot(nr, ny)
        normals.append((nr / length, ny / length))
    return normals


def sweep(profile: list[tuple[float, float]], outline: list[OutlinePoint] | None = None) -> Mesh:
    """Sweep a smooth profile ``[(offset from felt edge, height), ...]`` around the table."""
    outline = outline or stadium_outline()
    normals = _profile_normals(profile)
    # u follows the outline's length at the profile's outer edge; v follows the profile.
    reference = FELT_RADIUS + max(r for r, _ in profile)
    lengths = [0.0]
    for a, b in zip(outline, outline[1:] + outline[:1]):
        ax, az = a.cx + a.nx * reference, a.cz + a.nz * reference
        bx, bz = b.cx + b.nx * reference, b.cz + b.nz * reference
        lengths.append(lengths[-1] + math.hypot(bx - ax, bz - az))
    profile_lengths = [0.0]
    for (r0, y0), (r1, y1) in zip(profile, profile[1:]):
        profile_lengths.append(profile_lengths[-1] + math.hypot(r1 - r0, y1 - y0))

    vertices: list[float] = []
    # One extra ring closes the loop with its own texture coordinates.
    rings = outline + outline[:1]
    for i, point in enumerate(rings):
        for (offset, y), (nr, ny), v in zip(profile, normals, profile_lengths):
            radius = FELT_RADIUS + offset
            vertices += [
                point.cx + point.nx * radius, y, point.cz + point.nz * radius,
                point.nx * nr, ny, point.nz * nr,
                lengths[i] / 20.0, v / 20.0,
            ]
    columns = len(profile)
    indices: list[int] = []
    for i in range(len(outline)):
        for j in range(columns - 1):
            a = i * columns + j
            b = (i + 1) * columns + j
            indices += [a, b, a + 1, a + 1, b, b + 1]
    return Mesh(vertices, indices)


def felt(outline: list[OutlinePoint] | None = None) -> Mesh:
    """Flat stadium at ``y = 0``, slightly larger than the felt so the trim covers its edge."""
    outline = outline or stadium_outline()
    radius = FELT_RADIUS + 0.5
    vertices = [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]
    for p in outline:
        x, z = p.cx + p.nx * radius, p.cz + p.nz * radius
        vertices += [x, 0.0, z, 0.0, 1.0, 0.0, x / FELT_TILE, z / FELT_TILE]
    count = len(outline)
    indices: list[int] = []
    for i in range(count):
        indices += [0, 1 + (i + 1) % count, 1 + i]
    return Mesh(vertices, indices)


def rail_profile(steps: int = 20, exponent: float = 2.6) -> list[tuple[float, float]]:
    """Cross-section of the padded cushion: a superellipse sitting on the trim."""
    half = RAIL_WIDTH / 2
    centre = TRIM_WIDTH + half
    points = []
    for i in range(steps + 1):
        angle = math.pi * (1 - i / steps)  # inner edge first
        c, s = math.cos(angle), math.sin(angle)
        r = centre + half * math.copysign(abs(c) ** (2 / exponent), c)
        y = TRIM_HEIGHT + RAIL_HEIGHT * abs(s) ** (2 / exponent)
        points.append((r, y))
    return points


def build(part: str) -> Mesh:
    if part == "felt":
        return felt()
    if part == "trim":
        return sweep([(0.0, -0.2), (0.05, 0.35), (0.4, TRIM_HEIGHT), (TRIM_WIDTH + 0.2, TRIM_HEIGHT)])
    if part == "rail":
        return sweep(rail_profile())
    if part == "apron":
        outer = TRIM_WIDTH + RAIL_WIDTH
        return sweep([(outer - 0.3, TRIM_HEIGHT), (outer, TRIM_HEIGHT - 0.8),
                      (outer, -APRON_DEPTH + 1.0), (outer - 1.0, -APRON_DEPTH)])
    if part == "line":
        return sweep([(-BETTING_LINE_INSET, 0.04), (-BETTING_LINE_INSET + 0.35, 0.04)])
    raise ValueError(f"Unknown table part {part!r}; expected one of {PARTS}")
