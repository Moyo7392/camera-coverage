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


class _CoverageTree:
    """Range increments and the minimum coverage over all compressed atoms.

    Each node keeps its own uniform increment plus its children's minimum.
    Only the root minimum is queried, so lazy values need not be pushed down.
    """

    def __init__(self, size: int) -> None:
        self.size = size
        self.minimum = [0] * (4 * size)
        self.lazy = [0] * (4 * size)

    def add(self, start: int, end: int, delta: int) -> None:
        def update(node: int, left: int, right: int) -> None:
            if start <= left and right <= end:
                self.minimum[node] += delta
                self.lazy[node] += delta
                return
            middle = (left + right) // 2
            if start <= middle:
                update(2 * node, left, middle)
            if end > middle:
                update(2 * node + 1, middle + 1, right)
            self.minimum[node] = self.lazy[node] + min(
                self.minimum[2 * node], self.minimum[2 * node + 1])

        update(1, 0, self.size - 1)

    @property
    def fully_covered(self) -> bool:
        return self.minimum[1] > 0


def cameras_suffice(desired: Camera, cameras: Iterable[Camera]) -> bool:
    """Return whether every requested (distance, light) pair is supported.

    Each camera supports the Cartesian product of its two closed ranges. The
    software may choose a different camera for every shot. Units must agree.
    Lines and points are valid targets. Inputs are never changed.

    Time: O(n log n). Extra space: O(n).
    """
    if not isinstance(desired, Camera):
        raise TypeError("The desired characteristics must be a Camera.")

    left, right = desired.distance.minimum, desired.distance.maximum
    bottom, top = desired.light.minimum, desired.light.maximum
    rectangles = []
    light_edges = {bottom, top}
    for camera in cameras:
        if not isinstance(camera, Camera):
            raise TypeError("Each hardware camera must be a Camera.")
        x0 = max(left, camera.distance.minimum)
        x1 = min(right, camera.distance.maximum)
        y0 = max(bottom, camera.light.minimum)
        y1 = min(top, camera.light.maximum)
        if x0 <= x1 and y0 <= y1:
            rectangles.append((x0, x1, y0, y1))
            light_edges.update((y0, y1))

    if not rectangles:
        return False

    # Even indexes represent endpoints; odd indexes represent open gaps.
    # Keeping both makes a line/point target meaningful without area or epsilon.
    light_index = {value: 2 * i for i, value in enumerate(sorted(light_edges))}
    tree = _CoverageTree(2 * len(light_edges) - 1)
    events = {left: ([], []), right: ([], [])}
    for x0, x1, y0, y1 in rectangles:
        interval = (light_index[y0], light_index[y1])
        events.setdefault(x0, ([], []))[0].append(interval)
        events.setdefault(x1, ([], []))[1].append(interval)

    for distance in sorted(events):
        starts, ends = events[distance]
        for start, end in starts:
            tree.add(start, end, 1)
        # Starts and ends both cover this exact coordinate (closed ranges).
        if not tree.fully_covered:
            return False
        for start, end in ends:
            tree.add(start, end, -1)
        # Between this edge and the next, only the remaining cameras apply.
        if distance < right and not tree.fully_covered:
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

        def test_many_starts_and_ends_at_the_same_coordinate(self):
            hardware = [camera(0, 5, 0, 5), camera(0, 5, 5, 10),
                        camera(5, 10, 0, 3), camera(5, 10, 3, 10),
                        camera(5, 5, 0, 10)]
            self.assertTrue(cameras_suffice(self.target, hardware))
            self.assertFalse(cameras_suffice(self.target, hardware[1:]))

        def test_point_cameras_cannot_fill_an_open_gap(self):
            points = [camera(0, 10, y, y) for y in (0, 5, 10)]
            self.assertFalse(cameras_suffice(self.target, points))
            self.assertTrue(cameras_suffice(camera(0, 10, 5, 5), points))
            self.assertFalse(cameras_suffice(camera(0, 10, 5, 5),
                [camera(0, 0, 5, 5), camera(10, 10, 5, 5)]))

        def test_adjacent_representable_floats_still_leave_a_real_gap(self):
            from math import nextafter
            adjacent = nextafter(5.0, float('inf'))
            self.assertFalse(cameras_suffice(self.target,
                [camera(0, 10, 0, 5), camera(0, 10, adjacent, 10)]))
            self.assertFalse(cameras_suffice(self.target,
                [camera(0, 5, 0, 10), camera(adjacent, 10, 0, 10)]))

        def test_large_tiled_input_and_one_missing_strip(self):
            target = camera(0, 4000, 0, 10)
            strips = [camera(x, x + 1, 0, 10) for x in range(4000)]
            self.assertTrue(cameras_suffice(target, strips))
            self.assertFalse(cameras_suffice(target, strips[:2000] + strips[2001:]))

        def test_seeded_small_cases_against_independent_oracle(self):
            # Generated endpoints are integers. A half-unit lattice hits every
            # edge and every open cell in their arrangement, so it is an exact
            # oracle for these cases (not a production sampling algorithm).
            rng = random.Random(20260927)
            for case in range(5000):
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
                    # Coverage is invariant under order, duplication, and axis swap.
                    self.assertEqual(cameras_suffice(target, reversed(hardware)), expected)
                    self.assertEqual(cameras_suffice(target, hardware * 2), expected)
                    self.assertEqual(cameras_suffice(
                        Camera(target.light, target.distance),
                        [Camera(c.light, c.distance) for c in hardware]), expected)

    unittest.main(verbosity=2)
