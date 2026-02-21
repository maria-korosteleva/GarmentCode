# TODO — 1873 Selvedge Jeans Pattern

## Done

### 1. Add seam allowances to front, back, and yoke pieces

Added `_offset_polyline(pts, distance)` and `_draw_seam_allowance(ax, edges, scale)` helpers to `jeans_front.py`. SA is drawn as a continuous dashed gray cutting line in both debug and non-debug modes. Per-edge SA values follow the table below. Back and yoke SA edges are ordered CW (left-of-travel = outward).

| Piece | Edge | SA |
|-------|------|----|
| **Front** | Side seam | 3/4" |
| | Hem | 2 3/8" (1 1/2" turn-up + 7/8" hem) |
| | Inseam | 3/8" |
| | Crotch / fly | 3/8" |
| | Fly extension | additional 3/8" (waist to curve start) |
| | Waist | 3/8" |
| **Back** | Side seam | 3/4" |
| | Hem | 2 3/8" |
| | Inseam | 3/4" |
| | Seat seam | 5/8" |
| | Yoke seam | 3/4" |
| **Yoke (both)** | Long side / seat seam | 5/8" |
| | Short edge / side seam | 3/4" |
| | Waist and yoke seams | 3/8" |

### 2. Parameterize the 1873 back yoke gathering variation

Added `gathering_extension` parameter (default `0`) to `draft_jeans_yoke()` in `jeans_yoke_1873.py`. When > 0, extends `yoke_seat_dist` further along the seat_upper curve. Stored in metadata for use by the plot function.

### 3. Back seat_upper straightened

Changed `curve_seat_upper` from a cubic Bézier to a straight line (`back_waist` → `8_new`).

## Pending

### 4. Improve SA corner geometry

The current `_draw_seam_allowance` offsets each edge independently by its per-edge SA distance and concatenates the results. Corner treatment uses simple normal averaging (miter joins). Improve by computing proper line-line intersections at corners where adjacent edges meet, especially where SA widths differ (e.g. fly extension 3/4" meeting crotch 3/8").

Note: `pyclipper` (`PyclipperOffset`) was considered but only supports uniform offset for an entire polygon — it can't do per-edge SA widths. The current per-edge approach is correct; just the corner geometry needs refinement.
