# 1-Pleat Trouser Front — Drafting Instructions (MM&S Basic Block)

## Measurements

| Abbr | Description | Size 50 |
|------|-------------|---------|
| Wbg | Waistband girth | 88.0 cm |
| Hg | Hip girth | 102.0 cm |
| Hw | Hem width | 44.0 cm |
| Sl | Side length | 103.0 cm |
| Is | Inseam | 81.0 cm |

### Calculated Values

| Abbr | Formula | Size 50 |
|------|---------|---------|
| Br (body rise) | Sl - Is | 22.0 |
| Kh (knee height) | 1/2 Is + 1/10 Is - 2 | 46.6 |
| Ftw (front trouser width) | 1/4 Hg + 1 | 26.5 |
| Fcw (front crotch width) | 1/10 of 1/2 Hg + 1 | 6.1 |
| Cw (crotch width) | 1/4 Hg - 4 | 21.5 |
| Bcw (back crotch width) | Cw - Fcw | 15.4 |
| Btw (back trouser width) | 1/4 Hg + 3 | 28.5 |

## Coordinate System

- **A = (0, 0)** at bottom-left (hemline, left reference edge)
- **X axis**: positive to the right
- **Y axis**: positive upward

---

## Step 1: Framework

Mark point **A** at the origin (0, 0) — this is the hemline at the left reference edge.

From A, measure upward along the left reference line:
- **Knee line** at Kh = 46.6 cm
- **Crotch line** at Is = 81.0 cm
- **Waistline** at Sl = 103.0 cm

From the crotch line, measure upward:
- **Hipline** at 1/10 of 1/2 Hg + 3 = 8.1 cm above crotch = 89.1 cm from hem

Square right from each level to create 5 horizontal reference lines: hemline, knee line, crotch line, hipline, waistline.

**Output**: `trouser_front_step1.svg` — vertical reference + 5 horizontal lines with labels.

---

## Step 2: Widths and Creaseline

On the **hipline**, measure right from the left reference:
- **Ftw** = 26.5 cm → mark point, draw a perpendicular from waistline to crotch line.

From the Ftw point, measure right on the crotch line:
- **Fcw** = 6.1 cm → this is the **front crotch point** at (32.6, 81.0).

The **front creaseline** (grainline) runs vertically at the midpoint of the total width:
- creaseline x = (Ftw + Fcw) / 2 = 16.3 cm

Mark the halfway point between the hipline and crotch line (y = 85.0).

**Output**: `trouser_front_step2.svg` — adds Ftw perpendicular, crotch point, creaseline.

---

## Step 3: Hem Widths, Pleat, and Centre Front

On the **hemline**, measure from the creaseline:
- **1/4 Hw - 1** = 10.0 cm each side → sideseam hem at x = 6.3, inseam hem at x = 26.3
- **0.5 cm inward** from each → guideline marks at x = 6.8 and x = 25.8

On the **waistline**:
- **3.5 cm left** of creaseline → **pleat** mark at x = 12.8

On the **hipline**:
- **Ftw + 0.5** = 27.0 → **Centre Front (CF)** line, drawn vertically from hipline to waistline.

**Output**: `trouser_front_step3.svg` — adds hem points, pleat mark, CF line.

---

## Step 4: Shaping

At each hem edge, draw a short **perpendicular** ~4 cm tall (establishes hem squareness).

At the **knee line**:
- **1 cm wider** than hem on each side of creaseline → knee side at x = 5.3, knee inseam at x = 27.3

On the **Ftw perpendicular** (x = 26.5):
- **Fcw / 2** = 3.05 cm above the hipline → **crotch guide** at (26.5, 92.1)
- Draw a **slanted construction line** from crotch guide to the front crotch point.

The CF line extends downward from the hipline to where it meets the slanted line at (27.0, 91.2).

On the **waistline**, measure from CF leftward:
- **1/4 Wbg + 3.5 - 1.5** = 24.0 cm → **waist sideseam** at x = 3.0

**Output**: `trouser_front_step4.svg` — adds knee points, crotch guide, slanted line, waist sideseam.

---

## Step 5: Final Curves

**Raise the waistline** 0.7 cm at the sideseam → raised waist point at (3.0, 103.7).

Draw the following curves and outlines:

1. **Waistline curve**: from the raised sideseam (3.0, 103.7) to CF (27.0, 103.0). The curve arrives perpendicular to the CF line.

2. **Hip/sideseam curve**: from the mid-point between crotch and hip on the left reference (0, 85.0) upward to the raised waist (3.0, 103.7), with 1-1.25 cm intake (bows slightly inward).

3. **CF straight segment**: from CF at waist (27.0, 103.0) straight down to (27.0, 91.2).

4. **Crotch curve**: shallow Bezier from (27.0, 91.2) to the crotch point (32.6, 81.0).

5. **Inseam upper**: slightly hollow curve from crotch point (32.6, 81.0) to knee inseam (27.3, 46.6).

6. **Inseam lower**: straight from knee inseam (27.3, 46.6) to hem inseam (26.3, 0).

7. **Hemline**: straight from hem side (6.3, 0) to hem inseam (26.3, 0).

8. **Sideseam lower**: straight segments from mid-point (0, 85.0) → knee side (5.3, 46.6) → hem side (6.3, 0).

**Output**: `trouser_front_step5.svg` — complete pattern outline with all curves.
