# Camera coverage

`cameras_suffice(desired, cameras)` checks whether a set of hardware cameras can
capture **every** requested combination of subject distance and light level.
The implementation and its runnable tests are in
[`camera_coverage.py`](camera_coverage.py). Python 3.10+; no dependencies or UI.

```python
from camera_coverage import Camera, Range, cameras_suffice

desired = Camera(distance=Range(1, 10), light=Range(0, 100))
hardware = [
    Camera(distance=Range(1, 5), light=Range(0, 100)),
    Camera(distance=Range(5, 10), light=Range(0, 50)),
    Camera(distance=Range(5, 10), light=Range(50, 100)),
]
assert cameras_suffice(desired, hardware)
```

Run the tests:

```sh
python3 camera_coverage.py
```

## Reviewer notes

The important distinction is **two-dimensional coverage**. Covering the requested
distance range somewhere and the requested light range somewhere is not enough:
a nearby/bright camera and a distant/dark camera leave nearby/dark shots uncovered.
Likewise, covering four corners or the outer boundary can leave a hole inside.

## Phase 3: avoid rescanning every camera

The initial implementation was correct for the tested cases, but every distance
slab scanned all relevant cameras. With many narrow strips, that does quadratic
work. This revision keeps the same public function and uses a distance sweep
with a range-add/minimum segment tree: **O(n log n)** time, **O(n)** space.
The original implementation remains in the first commit for comparison.

### Representation and invariant

1. Clip each hardware rectangle to the requested rectangle; discard disjoint ones.
2. Sort the relevant light endpoints. Represent each endpoint and each open gap
   between endpoints as separate atoms. For endpoints `[0, 5, 10]`, the atoms are
   `{0}, (0,5), {5}, (5,10), {10}`. A camera covers a contiguous run of atoms.
3. Sweep distance endpoints. Add cameras that start there, then check coverage
   at that exact distance. Remove cameras that end there, then check the open
   distance interval up to the next event, if any.
4. Maintain a coverage count per light atom. The tree's root holds the minimum
   count across all atoms; a positive minimum means the whole slice is covered.

Starts must be added **before** checking the endpoint, and ends removed **after**
checking it, because ranges are closed. A zero-width camera contributes at its
one distance, but not in either neighboring open interval.

### Why the check is sufficient

Between consecutive distance endpoints the active camera set is constant.
Between consecutive light endpoints each active camera's coverage is constant.
Checking all resulting atoms therefore checks the continuous rectangle exactly.
No representative floating-point midpoint is needed, even when two endpoints
are adjacent representable floats. Keeping endpoints explicitly also handles
line and point targets; an area-only union check would miss those cases.

There are O(n) events and atoms. Each camera causes two O(log n) range updates;
checking the root is O(1). Sorting dominates the remaining work. The tree stores
uniform increments at each node plus the minimum of its children. Because only
the global minimum is queried, those increments do not need to be pushed down.

### Assumptions and tradeoffs

- A camera supports the full Cartesian product of its two ranges. There is no
  unspecified correlation between distance and light capability.
- Endpoints are inclusive. Touching intervals join; a positive gap does not.
- Units must match across inputs. Negative coordinates are allowed mathematically;
  a domain-specific caller can reject physically invalid units or values.
- Non-finite, reversed, non-numeric, and boolean endpoints are rejected. Empty
  hardware cannot cover even a point. Inputs are not mutated.
- Floating-point comparisons use the values supplied, with no arbitrary epsilon
  that could hide a real gap. If measurements have uncertainty, model that in the
  ranges before calling the function.
- The sweep/tree is more code than the original slab merge. For very small
  camera lists, the simpler original is still a reasonable choice; this revision
  makes the cost scale better without changing the range semantics.
- The production algorithm uses endpoint comparisons, not midpoints or grid
  sampling. This also avoids midpoint overflow for large finite coordinates.

### Validation

Tests include tiling, overlap, duplicates, irrelevant cameras, narrow gaps,
interior holes, boundary contact, lines/points, invalid inputs, and input order.
A seeded test also checks 5,000 small cases against an independent oracle. Those
cases have integer endpoints, so testing every point on a half-unit lattice
covers every boundary and open cell exactly. That oracle is restricted to the
generated tests; the production function works on continuous ranges.

The generated cases also check invariance under reordered input, duplicated
cameras, and exchanging the distance/light axes. Additional regressions cover
simultaneous starts/ends, point cameras, adjacent floating-point endpoints,
and 4,000 strips with and without one missing strip. All 15 tests run with the
standard library using the command above.

### Research

The general event-sweep pattern is described in
[Princeton's geometric intersection notes](https://algs4.cs.princeton.edu/93intersection/).
This implementation adapts that pattern to full coverage using minimum counts;
it does not use a rectangle-intersection routine as a coverage test.

### Small performance comparison

On this machine with Python 3.12.14, comparing the initial commit with this
revision on adjacent full-height strips (median of five runs):

| Cameras | Initial slab merge | Sweep/tree |
| --- | ---: | ---: |
| 100 | 0.108 ms | 0.122 ms |
| 1,000 | 7.880 ms | 1.220 ms |
| 4,000 | 119.200 ms | 5.849 ms |

This is one workload, not a universal speed claim or a timing-based test. The
small case shows the added setup cost; the larger cases expose repeated scans
in the original. Correctness tests, rather than these timings, gate the change.
