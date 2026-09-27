"""Check whether hardware cameras cover a requested distance/light rectangle.

Python 3.10+, standard library only. Run this file to execute the tests.
All ranges are closed: a camera rated [1, 3] supports both endpoints.
"""
from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class Range:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        for endpoint in (self.minimum, self.maximum):
            if isinstance(endpoint, bool) or not isinstance(endpoint, (int, float)):
                raise TypeError("Range endpoints must be real numbers, not booleans.")
            try:
                finite = isfinite(endpoint)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError("Range endpoints must be finite numbers.")
        if self.minimum > self.maximum:
            raise ValueError("Range minimum cannot exceed its maximum.")


@dataclass(frozen=True)
class Camera:
    distance: Range
    light: Range

    def __post_init__(self) -> None:
        if not isinstance(self.distance, Range) or not isinstance(self.light, Range):
            raise TypeError("Camera distance and light must be Range objects.")


def cameras_suffice(desired: Camera, cameras: Iterable[Camera]) -> bool:
    """Return whether every requested (distance, light) pair is supported.

    Each camera supports the Cartesian product of its two ranges. The software
    can choose a different hardware camera for every shot. Units must be
    consistent across the inputs. Zero-width ranges represent a line or point.

    Time: O(n^2). Extra space: O(n), including a copy of the iterable.
    The caller's input objects and collection are never changed.
    """
    if not isinstance(desired, Camera):
        raise TypeError("The desired characteristics must be a Camera.")
    hardware = list(cameras)
    if any(not isinstance(camera, Camera) for camera in hardware):
        raise TypeError("Each hardware camera must be a Camera.")

    left, right = desired.distance.minimum, desired.distance.maximum
    bottom, top = desired.light.minimum, desired.light.maximum
    relevant = [
        camera for camera in hardware
        if camera.distance.maximum >= left and camera.distance.minimum <= right
        and camera.light.maximum >= bottom and camera.light.minimum <= top
    ]

    # Between two consecutive camera edges, the set of active cameras cannot
    # change. Checking these slabs checks the continuum, not a sampled grid.
    edges = {left, right}
    for camera in relevant:
        edges.add(max(left, camera.distance.minimum))
        edges.add(min(right, camera.distance.maximum))
    edges = sorted(edges)
    slabs = zip(edges, edges[1:]) if left < right else [(left, right)]

    # Filtering preserves this order, so each slab needs only a linear merge.
    light_order = sorted(relevant, key=lambda c: (c.light.minimum, c.light.maximum))
    for slab_left, slab_right in slabs:
        intervals = (
            (camera.light.minimum, camera.light.maximum)
            for camera in light_order
            if camera.distance.minimum <= slab_left
            and camera.distance.maximum >= slab_right
        )
        covered_to = bottom
        covered = False
        for start, end in intervals:
            if end < covered_to:
                continue
            if start > covered_to:
                break  # A real light-level gap, even if another camera covers top.
            covered_to = max(covered_to, end)
            if covered_to >= top:
                covered = True
                break
        if not covered:
            return False
    return True


# Keep the runnable examples and tests here so the submission is one file.
if __name__ == "__main__":
    import random
    import unittest

    def camera(x0, x1, y0, y1):
        return Camera(Range(x0, x1), Range(y0, y1))

    class CoverageTests(unittest.TestCase):
        target = camera(0, 10, 0, 10)

        def test_one_camera_and_empty_input(self):
            self.assertTrue(cameras_suffice(self.target, [self.target]))
            self.assertTrue(cameras_suffice(self.target, [camera(-5, 15, -5, 15)]))
            self.assertFalse(cameras_suffice(self.target, []))

        def test_tiled_coverage_in_both_dimensions(self):
            tiles = [camera(x, x + 5, y, y + 5) for x in (0, 5) for y in (0, 5)]
            self.assertTrue(cameras_suffice(self.target, tiles))
            self.assertFalse(cameras_suffice(self.target, tiles[:-1]))

        def test_independent_axis_coverage_is_not_enough(self):
            diagonal = [camera(0, 5, 0, 5), camera(5, 10, 5, 10)]
            self.assertFalse(cameras_suffice(self.target, diagonal))

        def test_hole_despite_covered_corners_and_outer_edges(self):
            frame = [camera(0, 10, 0, 4), camera(0, 10, 6, 10),
                     camera(0, 4, 0, 10), camera(6, 10, 0, 10)]
            self.assertFalse(cameras_suffice(self.target, frame))

        def test_touching_ranges_are_continuous(self):
            self.assertTrue(cameras_suffice(self.target,
                [camera(0, 10, 0, 5), camera(0, 10, 5, 10)]))
            self.assertTrue(cameras_suffice(self.target,
                [camera(0, 5, 0, 10), camera(5, 10, 0, 10)]))

        def test_small_gaps_are_not_rounded_away(self):
            self.assertFalse(cameras_suffice(self.target,
                [camera(0, 5, 0, 10), camera(5.000000001, 10, 0, 10)]))
            self.assertFalse(cameras_suffice(self.target,
                [camera(0, 10, 0, 5), camera(0, 10, 5.000000001, 10)]))

        def test_overlap_duplicates_clipping_and_order(self):
            hardware = [camera(4, 20, -5, 15), camera(-10, 6, 0, 10)]
            original = hardware.copy()
            self.assertTrue(cameras_suffice(self.target, hardware))
            self.assertEqual(hardware, original)
            self.assertTrue(cameras_suffice(self.target, iter(hardware[::-1] * 2)))
            self.assertFalse(cameras_suffice(self.target, [camera(11, 12, 0, 10)]))

        def test_lines_and_points(self):
            self.assertTrue(cameras_suffice(camera(2, 2, 0, 10),
                [camera(2, 2, 0, 4), camera(2, 2, 4, 10)]))
            self.assertFalse(cameras_suffice(camera(2, 2, 0, 10),
                [camera(2, 2, 0, 4), camera(2, 2, 5, 10)]))
            self.assertTrue(cameras_suffice(camera(0, 10, 2, 2),
                [camera(0, 5, 2, 2), camera(5, 10, 2, 2)]))
            self.assertTrue(cameras_suffice(camera(1, 1, 1, 1), [camera(1, 1, 1, 1)]))
            self.assertFalse(cameras_suffice(camera(1, 1, 1, 1), []))
            self.assertFalse(cameras_suffice(self.target, [camera(5, 5, 0, 10)]))

        def test_negative_coordinates_and_large_finite_values(self):
            self.assertTrue(cameras_suffice(camera(-5, -1, -3, -1),
                [camera(-6, 0, -4, 0)]))
            huge = camera(-1e308, 1e308, -1e308, 1e308)
            self.assertTrue(cameras_suffice(huge, [huge]))

        def test_invalid_input(self):
            for bounds in [(2, 1), (float('nan'), 1), (0, float('inf'))]:
                with self.assertRaises(ValueError):
                    Range(*bounds)
            for bounds in [(True, 1), ('0', 1), (None, 1)]:
                with self.assertRaises(TypeError):
                    Range(*bounds)
            with self.assertRaises(TypeError):
                Camera((0, 1), Range(0, 1))
            with self.assertRaises(TypeError):
                cameras_suffice(self.target, [None])

        def test_seeded_small_cases_against_independent_oracle(self):
            # Generated endpoints are integers. A half-unit lattice hits every
            # edge and every open cell in their arrangement, so it is an exact
            # oracle for these cases (not a production sampling algorithm).
            rng = random.Random(20260927)
            for case in range(1000):
                def generated():
                    x0, x1 = sorted(rng.choices(range(-2, 5), k=2))
                    y0, y1 = sorted(rng.choices(range(-2, 5), k=2))
                    return camera(x0, x1, y0, y1)
                target = generated()
                hardware = [generated() for _ in range(rng.randrange(9))]
                expected = all(
                    any(c.distance.minimum <= x / 2 <= c.distance.maximum
                        and c.light.minimum <= y / 2 <= c.light.maximum
                        for c in hardware)
                    for x in range(2 * target.distance.minimum, 2 * target.distance.maximum + 1)
                    for y in range(2 * target.light.minimum, 2 * target.light.maximum + 1)
                )
                with self.subTest(case=case):
                    self.assertEqual(cameras_suffice(target, hardware), expected)

    unittest.main(verbosity=2)
