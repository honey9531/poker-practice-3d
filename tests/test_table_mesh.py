"""Meshes for the 3D table (pure Python)."""

import math

import pytest

from services import table_mesh as tm


@pytest.mark.parametrize("part", tm.PARTS)
def test_every_part_is_a_valid_triangle_mesh(part):
    mesh = tm.build(part)
    assert len(mesh.vertices) % tm.FLOATS_PER_VERTEX == 0
    assert mesh.indices and len(mesh.indices) % 3 == 0
    assert 0 <= min(mesh.indices) and max(mesh.indices) < mesh.vertex_count
    for nx, ny, nz in mesh.normals():
        assert math.isclose(math.hypot(nx, ny, nz), 1.0, rel_tol=1e-6)


@pytest.mark.parametrize("part", tm.PARTS)
def test_no_degenerate_triangles(part):
    mesh = tm.build(part)
    points = mesh.positions()
    for i in range(0, len(mesh.indices), 3):
        a, b, c = (points[j] for j in mesh.indices[i:i + 3])
        ab = [b[k] - a[k] for k in range(3)]
        ac = [c[k] - a[k] for k in range(3)]
        cross = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0])
        assert math.hypot(*cross) > 1e-6


def test_table_fits_its_published_outer_size():
    low, high = tm.build("apron").bounds()
    assert math.isclose(high[0] - low[0], tm.OUTER_WIDTH, abs_tol=0.01)
    assert math.isclose(high[2] - low[2], tm.OUTER_DEPTH, abs_tol=0.01)
    for part in tm.PARTS:
        low, high = tm.build(part).bounds()
        assert low[0] >= -tm.OUTER_WIDTH / 2 - 0.01 and high[0] <= tm.OUTER_WIDTH / 2 + 0.01
        assert low[2] >= -tm.OUTER_DEPTH / 2 - 0.01 and high[2] <= tm.OUTER_DEPTH / 2 + 0.01


def test_felt_is_flat_and_faces_up():
    mesh = tm.build("felt")
    assert {y for _, y, _ in mesh.positions()} == {0.0}
    assert set(mesh.normals()) == {(0.0, 1.0, 0.0)}
    low, high = mesh.bounds()
    # Reaches under the trim all the way round.
    assert high[0] >= tm.STRAIGHT_HALF + tm.FELT_RADIUS
    assert high[2] >= tm.FELT_RADIUS


def test_rail_is_a_raised_cushion_around_the_felt():
    mesh = tm.build("rail")
    top = max(y for _, y, _ in mesh.positions())
    assert math.isclose(top, tm.TRIM_HEIGHT + tm.RAIL_HEIGHT, rel_tol=1e-6)
    # The highest points face up; nothing reaches into the felt.
    for (x, y, z), normal in zip(mesh.positions(), mesh.normals()):
        if y == top:
            assert normal[1] > 0.99
        cx = max(-tm.STRAIGHT_HALF, min(tm.STRAIGHT_HALF, x))
        assert math.hypot(x - cx, z) >= tm.FELT_RADIUS + tm.TRIM_WIDTH - 1e-6


def test_swept_parts_are_closed_loops():
    profile = tm.rail_profile()
    mesh = tm.sweep(profile)
    points = mesh.positions()
    columns = len(profile)
    first, last = points[:columns], points[-columns:]
    for a, b in zip(first, last):
        assert all(math.isclose(a[k], b[k], abs_tol=1e-9) for k in range(3))


def test_outline_normals_point_outwards():
    for p in tm.stadium_outline():
        assert math.isclose(math.hypot(p.nx, p.nz), 1.0)
        # Moving along the normal leaves the spine (the segment between the ends' centres).
        assert abs(p.cx) == tm.STRAIGHT_HALF and p.cz == 0.0
        assert p.nx * math.copysign(1, p.cx) >= -1e-9


def test_unknown_part_is_rejected():
    with pytest.raises(ValueError):
        tm.build("legs")
