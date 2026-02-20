# DXF Export for Jeans Pattern Panels

## Goal

Add a `export_dxf.py` module that converts the front/back jeans drafts into a
`.dxf` file suitable for laser cutters, plotters, or CAD software (LibreCAD,
FreeCAD, etc.).

Currently the only output is **matplotlib PNG** via `plot_jeans_front()` /
`plot_jeans_back()`. There is no DXF support anywhere in the codebase.

---

## Data Structures (as produced by the drafting code)

### Front panel (`draft_jeans_front()` return dict)

**Points** (dict of `np.array([x, y])`):

| Key   | Description                |
|-------|----------------------------|
| `0`   | Hem, outseam side          |
| `1`   | Waist, outseam side        |
| `2`   | Baseline / hip level       |
| `3`   | Knee level                 |
| `4`   | Seat level                 |
| `0'`  | Hem, inseam side           |
| `3'`  | Knee, inseam side          |
| `5`   | Crotch fork base           |
| `6`   | Crotch-to-inseam junction  |
| `7`   | Rise reference             |
| `8`   | Crotch fork top            |
| `1*`  | Adjusted waist (hip curve start / rise curve start) |
| `7*`  | Adjusted rise end          |
| `9`   | Crotch curve control ref   |
| `10`  | Center-front reference     |
| `temp`| Construction helper (ignore)|

**Curves** (dict of `(100, 2)` sampled numpy arrays):

| Key       | Type   | Endpoints        | Description          |
|-----------|--------|------------------|----------------------|
| `hip`     | cubic  | `1*` -> `4`      | Side hip curve       |
| `rise`    | cubic  | `1*` -> `7*`     | Front rise curve     |
| `crotch`  | quad   | `8` -> `6`       | Crotch curve (via 9) |
| `inseam`  | cubic  | `6` -> `3'`      | Inseam curve         |

**Construction** (dict): `fly_start`, `fly_end`

### Back panel (`draft_jeans_back()` return dict)

**Points**:

| Key             | Description                     |
|-----------------|---------------------------------|
| `back_hem`      | Hem, inseam side                |
| `11`            | Crotch-inseam junction (back)   |
| `12`            | Lower inseam endpoint           |
| `2_new`         | Adjusted baseline pt2           |
| `8_new`         | Extended seat/crotch fork       |
| `back_waist`    | Back waist endpoint             |
| `waist_seat_x`  | Waist-seat intersection         |

**Curves**:

| Key            | Type  | Endpoints              | Description          |
|----------------|-------|------------------------|----------------------|
| `seat_upper`   | cubic | `back_waist` -> `8_new`| Upper seat seam      |
| `seat_lower`   | cubic | `8_new` -> `11`        | Lower seat seam      |
| `back_inseam`  | cubic | `11` -> `12`           | Back inseam curve    |

**Construction** (dict): `inseam_line_start/end`, `seat_line_start/end`,
`seat_angle_start/end`, `waist_line_start/end`

---

## Outline Edge Sequences

These mirror the drawing order in `plot_jeans_front()` / `plot_jeans_back()`.

### Front panel (closed loop)

Walk **counter-clockwise** starting at the waist:

| #  | Segment                | Source                  | DXF entity |
|----|------------------------|-------------------------|------------|
| 1  | `1*` -> `4`            | `curves['hip']`         | SPLINE     |
| 2  | `4` -> `0`             | straight                | LINE       |
| 3  | `0` -> `0'`            | straight                | LINE       |
| 4  | `0'` -> `3'`           | straight                | LINE       |
| 5  | `3'` <- `6` (reversed) | `curves['inseam']`      | SPLINE     |
| 6  | `6` <- `8` (reversed)  | `curves['crotch']`      | SPLINE     |
| 7  | `8` <- `7*`            | straight                | LINE       |
| 8  | `7*` -> `1*`           | `curves['rise']` (rev.) | SPLINE     |

> Note: curves are stored start->end as listed in the table above. Some
> segments need to be reversed to form a continuous loop. For SPLINE
> `fit_points`, just reverse the array.

### Back panel (closed loop)

The back panel shares some front-panel points (`1`, `0`, `4`) for the outseam.

| #  | Segment                    | Source                     | DXF entity |
|----|----------------------------|----------------------------|------------|
| 1  | `1` (front) -> `back_waist`| straight (waist line)      | LINE       |
| 2  | `back_waist` -> `8_new`    | `curves['seat_upper']`     | SPLINE     |
| 3  | `8_new` -> `11`            | `curves['seat_lower']`     | SPLINE     |
| 4  | `11` -> `12`               | `curves['back_inseam']`    | SPLINE     |
| 5  | `12` -> `back_hem`         | straight                   | LINE       |
| 6  | `back_hem` -> `0` (front)  | straight                   | LINE       |
| 7  | `0` -> `4` (front)         | straight                   | LINE       |
| 8  | `4` -> `1` (front)         | straight                   | LINE       |

---

## Implementation Plan

### Dependency

- **`ezdxf`** (standard Python DXF library, MIT licensed)
- Add to `setup.cfg` `install_requires` or `pip install ezdxf` locally

### New file: `custom/garment_programs/export_dxf.py`

```python
import ezdxf
import numpy as np

def export_jeans_dxf(front_draft, back_draft, path='Logs/jeans.dxf'):
    """Export front and back jeans panels to a DXF file.

    Parameters
    ----------
    front_draft : dict  — output of draft_jeans_front()
    back_draft  : dict  — output of draft_jeans_back()
    path        : str   — output file path
    """
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # Layers
    doc.layers.add('FRONT', color=1)          # red
    doc.layers.add('BACK', color=5)           # blue
    doc.layers.add('CONSTRUCTION', color=8)   # gray

    _add_front_panel(msp, front_draft, layer='FRONT')
    _add_back_panel(msp, front_draft, back_draft, layer='BACK',
                    x_offset=<enough to clear front panel>)
    _add_construction(msp, front_draft, back_draft, layer='CONSTRUCTION')

    doc.saveas(path)
```

### Curve strategy: SPLINE with fit_points

All curves are stored as 100-point sampled Bézier polylines. Two options:

1. **`fit_points`** — pass the sampled points directly to
   `msp.add_spline(fit_points=...)`. The CAD app fits a smooth spline through
   them. Easiest, and with 100 points the result is visually identical.

2. **Native Bézier control points** — recover the original P0..P3 from the
   drafting code and emit `msp.add_spline()` with `control_points` and
   `knots`. More CAD-editable, but requires refactoring the draft functions
   to also return control points (they currently only return sampled arrays).

**Recommendation:** Start with option 1 (fit_points from sampled arrays).
It requires no changes to the drafting code. If CAD editability matters later,
refactor the draft functions to also return control points and switch to
option 2.

> With 100 fit_points the spline will be indistinguishable from the true
> Bézier, and the DXF file stays under 50 KB.

### Panel separation

Translate the back panel by `x_offset` so the two panels don't overlap in the
DXF. Compute the offset as:

```python
front_max_x = max(pt[0] for pt in front_draft['points'].values()) + margin
```

### Construction geometry (CONSTRUCTION layer)

For each panel, add dashed reference lines on a separate layer:

**Front panel:**
- Seat line — vertical at `pts['4']` x
- Hip line — vertical at `pts['2']` x
- Knee line — vertical at `pts['3']` x
- Center-front — horizontal at `pts['10']` y

**Back panel:**
- Same vertical references (offset by `x_offset`)

These lines use linetype `DASHED` and go on layer `CONSTRUCTION`.

### Integration

Wire into the back panel's `run()` function (the main entry point):

```python
# In jeans_back.py run():
def run(measurements_path, output_path, debug=False):
    m = load_measurements(measurements_path)
    front = draft_jeans_front(m)
    back = draft_jeans_back(m, front)
    plot_jeans_back(front, back, output_path, debug=debug)

    # DXF export (optional — guarded by import)
    try:
        from .export_dxf import export_jeans_dxf
        dxf_path = output_path.replace('.png', '.dxf')
        export_jeans_dxf(front, back, path=dxf_path)
    except ImportError:
        pass  # ezdxf not installed, skip
```

Or add a separate `run_dxf()` entry point to keep concerns separate.

---

## Verification

1. `pip install ezdxf`
2. Run the export -> produces `Logs/jeans.dxf`
3. Open in a DXF viewer (LibreCAD, FreeCAD, or sharecad.org):
   - Both panels visible on separate layers
   - Closed outlines (no gaps)
   - Curves smooth (not faceted)
   - Dimensions match the PNG output
4. Toggle layers in CAD to isolate front/back/construction

---

## Bézier Control Points Reference

For future option 2 (native control points), here are the original definitions:

### Front curves

**hip** (cubic): `P0=1*, P1=1*+[d/3, rise], P2=4-[d/3, 0], P3=4`

**rise** (cubic): `P0=1*, P1=1*+[0, -d/3], P2=7*+[0, d/3], P3=7*`

**crotch** (quadratic): `P0=8, P1=2*pt9-0.5*(pt8+pt6), P2=6`

**inseam** (cubic): `P0=6, P1=6+tan_at_6*(d/4), P2=3'-straight_dir*(d/4), P3=3'`
  - `tan_at_6` = direction 6->3' rotated 20 degrees
  - `straight_dir` = direction 0'->3' (normalized)

### Back curves

**back_inseam** (cubic): `P0=11, P1=11+tan*(d/4), P2=12-straight*(d/4), P3=12`
  - `tan` = direction 11->12 rotated 15 degrees
  - `straight` = direction back_hem_inseam->12 (normalized)

**seat_upper** (cubic): `P0=back_waist, P1=back_waist+waist_perp*(d/3), P2=8_new+seat_angle_dir*(d/3), P3=8_new`

**seat_lower** (cubic): `P0=8_new, P1=8_new+seat_to_crotch*(d/3), P2=11+perp_inseam*(d/3), P3=11`
