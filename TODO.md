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

### 4. Front waist curve (1*→7*) fixed to true C-curve

Replaced the previous chord-direction + perpendicular-offset cubic with a cubic whose
control points produce tangents pointing purely in the −y direction (toward the side seam)
at both endpoints. Because the x-component of the Bézier becomes `6*(1-t)*t*(Δx)` — always
non-negative — the curve is monotone in x, guaranteed inflection-free, and naturally bows
toward the hem at the midpoint (the classic "waist dip"). The bottom of the curve flows
toward the side seam, as required.

### 5. Back inseam curve (11→12) tangent fixed

The arrival tangent at pt12 previously used `back_hem_inseam` (a construction-line point)
instead of the actual straight-segment endpoint `back_hem`. Fixed so the curve flows
smoothly into the 12→back_hem straight segment with no kink.

**Why the back inseam is 1/4" shorter than the front (by design):**
The front curved inseam (6→3') is 1/4" longer than the back curved inseam (11→12).
When sewn together, the front is *eased* into the back (not stretched — denim is woven).
The 1/4" distributes across the curved section, causing the sewn seam to bow slightly
forward. This matches the natural forward hang of the leg, prevents the common "leg twist"
problem in trousers, and is a standard tailoring technique for curved inseams.

### 6. verify_draft() added

`verify.py` implements the "Double Checking Your Work" checks from the lesson:

| Check | What is measured |
|-------|-----------------|
| Waist | (front arc + back straight − 3/4") × 2 vs target waist |
| Hips | horizontal width at seat level (4→8 front, 4→8_new back) × 2 vs seat + ease |
| Fly & seat | seam lengths minus 1½" waistband (reference only) |
| Lengths | side seam (arc + straight) and front inseam vs targets; back curved inseam ≈ front − ¼" |
| Widths | full hem and knee opening vs targets |

**Note on back waist:** The back panel currently includes the full back from waist to seat
(the yoke area is part of the back panel draft). So the back waist seam (`1 → back_waist`)
is used for the waist check. When the yoke is carved out as a separate piece later, this
measurement will need to come from the yoke's top edge instead.

Run via: `python3 -m custom.run -m custom/measurements/justin.yaml -p SelvedgeJeans1873.verify`

## Pending

### 7. Improve SA corner geometry

The current `_draw_seam_allowance` offsets each edge independently by its per-edge SA distance and concatenates the results. Corner treatment uses simple normal averaging (miter joins). Improve by computing proper line-line intersections at corners where adjacent edges meet, especially where SA widths differ (e.g. fly extension 3/4" meeting crotch 3/8").

Note: `pyclipper` (`PyclipperOffset`) was considered but only supports uniform offset for an entire polygon — it can't do per-edge SA widths. The current per-edge approach is correct; just the corner geometry needs refinement.

### 8. Add 1873 style parameter

Some measurements and piece selections have 1873-specific variants mentioned in the instructions:
- **Hem width**: "in the original 1873 example the hem matched the knee for a very square and full cut" → `hem_width = knee_width`
- **Yoke**: 1873 uses the gathering yoke (`jeans_yoke_1873.py`) vs the modern flat yoke
- **Potentially others** as more variants are discovered

Add a `style='1873'` (or similar) code-level parameter that automatically applies these period-correct choices as a group, so you can switch between a faithful 1873 cut and a more modern interpretation.
