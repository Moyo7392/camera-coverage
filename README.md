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

Each camera is a closed rectangle. Split the desired distance range at every
relevant camera's distance endpoint. Inside any resulting slab, the active
camera set is constant. Select cameras that span that entire slab and merge their
light intervals. If those intervals fail to cover the desired light range, the
proposal fails. Otherwise, continue through every slab.

### Why the check is sufficient

There is no camera edge strictly inside a slab. A camera covering an interior
distance therefore spans the full slab. Its light interval is available at every
distance there. Merging these intervals exactly checks the requested vertical
slice. If each slab is covered, their union covers the desired rectangle.
Closed ranges mean their shared boundaries are covered too. Conversely, a failed
slab has an uncovered distance/light pair, so returning false is necessary.
For a zero-width distance target, the same interval merge checks that one line;
zero-height targets and single points work without an area-based shortcut.

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
- Complexity is **O(n²)** time and **O(n)** additional space: sort cameras by
  light-range start once, then linearly filter/merge for each of O(n) slabs. An event sweep with a
  coverage tree could improve the bound for very large proposals, but adds
  machinery that is unnecessary for a straightforward camera selection check.
- The production algorithm uses endpoint comparisons, not midpoints or grid
  sampling. This also avoids midpoint overflow for large finite coordinates.

### Validation

Tests include tiling, overlap, duplicates, irrelevant cameras, narrow gaps,
interior holes, boundary contact, lines/points, invalid inputs, and input order.
A seeded test also checks 1,000 small cases against an independent oracle. Those
cases have integer endpoints, so testing every point on a half-unit lattice
covers every boundary and open cell exactly. That oracle is restricted to the
generated tests; the production function works on continuous ranges.
