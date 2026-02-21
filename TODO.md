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

### 4. Replace SA offset with pyclipper

The current `_offset_polyline` uses simple normal averaging with miter joins. Replace with `pyclipper.PyclipperOffset` for proper corner treatment (square/round joins, clean transitions where SA widths change, self-intersection cleanup).

### 5. Commit all uncommitted changes

Everything since the SVG switch commit (`83f2188`) is uncommitted:
- 6 new piece modules: `jeans_waistband.py`, `jeans_fly_1873.py`, `jeans_fly_one_piece.py`, `jeans_front_pocket.py`, `jeans_back_pocket.py`, `jeans_back_cinch.py`
- 4 instruction markdown files: `jeans_waistband_instructions.md`, `jeans_fly_instructions.md`, `jeans_pocket_instructions.md`, `jeans_back_cinch_instructions.md`
- Updated `__init__.py` (10 pieces)
- SA helpers and per-piece SA drawing
- Gathering extension parameter on 1873 yoke
- Back seat_upper straightened
- Front pocket direction fix + points on outline
- Back pocket pentagon shape with exact dimensions
- Yoke non-debug mode (hide back panel context)
- Fly rename (modern → one-piece)
