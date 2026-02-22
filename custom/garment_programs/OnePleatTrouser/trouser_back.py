"""
1-Pleat Trouser Back Panel (MM&S Basic Block)

Based on: MM&S - Basic Block: Trousers with 1 Pleat - Back Pattern
Drafted on top of the front panel, using front geometry as reference.

Coordinate system (same as front):
  - Origin A at bottom-left (hemline, left reference edge)
  - X axis: positive to the right
  - Y axis: positive upward
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .trouser_front import (
    INCH, load_measurements, draft_trouser_front,
    _bezier_cubic, _bezier_quad, _curve_length, _annotate_len,
)


# -- Design parameters -------------------------------------------------------
#
# The slant of the back trouser pattern:
#   Choose the slant of the centre back and therefore the fit, as preferred
#   by the customer and according to the preferred silhouette.
#   - Straighter back → more accurate fit, especially while standing.
#   - More slanted back → considerably more length, increasing wearing
#     comfort especially in a sitting position.
#   - Wide seat → needs more length + width (= more slanted).
#   - Flat seat → needs the opposite (= straighter).
#
# Both CREASELINE_SHIFT and CB_SLANT control the slant together.
# Increase both for a straighter pattern; decrease both for more slant.

# Back creaseline shift: 1–1.5 cm rightward from front creaseline.
# Larger values → straighter CB (more upright back pattern).
# Smaller values → more slanted CB.
# Use larger values for larger sizes to keep the proportion equal.
CREASELINE_SHIFT = 1.0    # 1 cm to 1.5 cm
# CB slant: 2–3 cm upward from crotch line along sideseam.
# Larger values → straighter CB; smaller → more slanted CB.
CB_SLANT = 2.0             # 2 cm to 3 cm
LEG_EXTENSION = 2.0       # cm parallel to each seam, knee to hem
CB_HEIGHT_EXTRA = 0.5     # cm added to back waist height at CB
# Sideseam intake at the waist: 1–1.5 cm.
# The dart sizes are computed from this to balance the waist check.
# MM&S note on Maximal Intake: "The hip curve should be shallow and not too
# round. Adjust the calculation if necessary: reduce the ease at the front
# trouser width or change the pleat intake or the seam relocation."
SIDESEAM_INTAKE = 1.25    # 1 cm to 1.5 cm
DART_LARGE_RATIO = 0.55   # larger dart gets 55% of total dart intake
DART_LARGE_LEN = 9.5      # cm
DART_SMALL_LEN = 7.5      # cm


# -- Drafting ----------------------------------------------------------------

def draft_trouser_back(m, front, creaseline_shift=CREASELINE_SHIFT,
                       cb_slant=CB_SLANT):
    """
    Compute all geometry for the 1-pleat trouser back.

    Parameters
    ----------
    m : dict   Measurements in cm (from load_measurements).
    front : dict   Result of draft_trouser_front(m).
    creaseline_shift : float
        Back creaseline offset (1–1.5 cm) rightward from front creaseline.
        Larger → straighter CB; smaller → more slanted CB.
        Increase for larger sizes to keep proportionally equal.
    cb_slant : float
        CB slant (2–3 cm) upward from crotch line along sideseam.
        Larger → straighter CB; smaller → more slanted CB.

    Returns
    -------
    dict with keys: points, levels, construction, curves, measurements, metadata
    """
    fpts = front['points']
    flvl = front['levels']
    fcon = front['construction']
    fmm  = front['measurements']

    # -- Measurements from front --
    Btw = fmm['Btw']      # back trouser width (hip level, half)
    Bcw = fmm['Bcw']      # back crotch width
    Hg  = fmm['Hg']       # hip girth
    Wbg = fmm['Wbg']      # waist girth

    Tbtw = Btw + Bcw       # total back trouser width

    hem_y    = flvl['hemline']
    knee_y   = flvl['knee line']
    crotch_y = flvl['crotch line']
    hip_y    = flvl['hipline']
    waist_y  = flvl['waistline']

    # ================================================================
    # Step 1: Trace Front + Extend Legs + Back Creaseline + CB Slant
    # ================================================================

    # -- Leg extension: 2 cm perpendicular to each seam (knee→hem) --
    # Sideseam: knee_side → hem_side_top
    f_knee_side = fpts['knee_side']
    f_hem_side_top = fpts['hem_side_top']
    side_dir = f_hem_side_top - f_knee_side
    side_unit = side_dir / np.linalg.norm(side_dir)
    # Outward perpendicular (leftward for sideseam)
    side_perp = np.array([-side_unit[1], side_unit[0]])
    if side_perp[0] > 0:
        side_perp = -side_perp  # ensure leftward
    back_knee_side = f_knee_side + side_perp * LEG_EXTENSION
    back_hem_side_top = f_hem_side_top + side_perp * LEG_EXTENSION
    back_hem_side = fpts['hem_side'] + side_perp * LEG_EXTENSION

    # Inseam: knee_inseam → hem_inseam_top
    f_knee_inseam = fpts['knee_inseam']
    f_hem_inseam_top = fpts['hem_inseam_top']
    inseam_dir = f_hem_inseam_top - f_knee_inseam
    inseam_unit = inseam_dir / np.linalg.norm(inseam_dir)
    # Outward perpendicular (rightward for inseam)
    inseam_perp = np.array([inseam_unit[1], -inseam_unit[0]])
    if inseam_perp[0] < 0:
        inseam_perp = -inseam_perp  # ensure rightward
    back_knee_inseam = f_knee_inseam + inseam_perp * LEG_EXTENSION
    back_hem_inseam_top = f_hem_inseam_top + inseam_perp * LEG_EXTENSION
    back_hem_inseam = fpts['hem_inseam'] + inseam_perp * LEG_EXTENSION

    # -- Back creaseline stays at front creaseline (it's the grainline) --
    back_creaseline_x = fcon['creaseline_x']
    # Construction mark 1–1.5 cm to the right: centre for width distribution
    width_center_x = back_creaseline_x + creaseline_shift

    # -- CB slant origin: 2–3 cm up from crotch line on sideseam (x=0) --
    cb_slant_origin = np.array([0.0, crotch_y + cb_slant])

    # ================================================================
    # Step 2: Width Distribution on Hipline
    # ================================================================
    half_Tbtw = Tbtw / 2
    back_hip_side = np.array([width_center_x - half_Tbtw, hip_y])
    back_hip_inseam = np.array([width_center_x + half_Tbtw, hip_y])
    bcw_mark = np.array([back_hip_inseam[0] - Bcw, hip_y])  # CB meets hipline
    back_crotch_pt = np.array([back_hip_inseam[0], crotch_y])

    # ================================================================
    # Step 3: Connect Knee to Hip Widths + CB Direction
    # ================================================================
    # CB guideline: from cb_slant_origin to bcw_mark
    cb_guideline_dir = bcw_mark - cb_slant_origin
    # CB direction: perpendicular to guideline, pointing upward
    cb_perp = np.array([-cb_guideline_dir[1], cb_guideline_dir[0]])
    cb_perp_unit = cb_perp / np.linalg.norm(cb_perp)
    if cb_perp_unit[1] < 0:
        cb_perp_unit = -cb_perp_unit  # ensure upward

    # ================================================================
    # Step 4: Transfer Lengths + Determine Back Waist Height
    # ================================================================

    # -- Back inseam length transfer --
    # Front inseam: crotch_pt → knee_inseam (upper curve)
    front_inseam_len = _curve_length(front['curves']['inseam_upper'])
    back_inseam_target = front_inseam_len - 0.7

    # Back inseam direction: back_knee_inseam → back_hip_inseam
    back_inseam_dir = back_hip_inseam - back_knee_inseam
    back_inseam_unit = back_inseam_dir / np.linalg.norm(back_inseam_dir)
    # Place back crotch point at target distance from back_knee_inseam along this line
    back_crotch_pt = back_knee_inseam + back_inseam_unit * back_inseam_target

    # -- Back sideseam length transfer --
    # Front sideseam: mid_side → hip (straight) + hip → waist_raised (curve)
    front_side_straight = np.linalg.norm(fpts['hip_side'] - fpts['mid_side'])
    front_side_curve = _curve_length(front['curves']['hip'])
    front_side_total = front_side_straight + front_side_curve

    # Back sideseam guideline: back_knee_side → back_hip_side, extended upward
    back_side_dir = back_hip_side - back_knee_side
    back_side_unit = back_side_dir / np.linalg.norm(back_side_dir)
    # Distance from back_knee_side to back_hip_side
    knee_to_hip_dist = np.linalg.norm(back_side_dir)
    # Front sideseam from knee: add knee→mid_side portion
    front_knee_to_mid = np.linalg.norm(fpts['mid_side'] - fpts['knee_side'])
    front_side_from_knee = front_knee_to_mid + front_side_total
    # Place back_waist_side at total front length from back_knee_side
    back_waist_side = back_knee_side + back_side_unit * front_side_from_knee

    # -- CB waist height --
    # Measure from back creaseline at knee level (Pp) to back_waist_side
    back_creaseline_knee = np.array([back_creaseline_x, knee_y])
    waist_side_height = np.linalg.norm(back_waist_side - back_creaseline_knee)
    # Transfer that distance + 0–1 cm from Pp to the CB line.
    # Find the point on the CB line (through bcw_mark in cb_perp_unit direction)
    # at distance (waist_side_height + extra) from Pp.
    R = waist_side_height + CB_HEIGHT_EXTRA
    d = bcw_mark - back_creaseline_knee
    u = cb_perp_unit
    # Solve |d + t*u|^2 = R^2  →  t^2 + 2(d·u)t + (|d|^2 - R^2) = 0
    a_coeff = 1.0
    b_coeff = 2.0 * np.dot(d, u)
    c_coeff = np.dot(d, d) - R * R
    discrim = b_coeff**2 - 4 * a_coeff * c_coeff
    t_cb = (-b_coeff + np.sqrt(discrim)) / (2 * a_coeff)  # positive root (upward)
    back_cb_waist = bcw_mark + t_cb * cb_perp_unit

    # ================================================================
    # Step 5: Waistline + Darts Layout
    # ================================================================
    # Waistline from back_waist_side to back_cb_waist
    waist_vec = back_cb_waist - back_waist_side
    waist_len = np.linalg.norm(waist_vec)
    waist_unit = waist_vec / waist_len

    # -- Waist measurement (MM&S procedure) --
    # Transfer front waist minus pleat from CB to the right (extending past CB)
    front_waist_curve_len = _curve_length(front['curves']['waistline'])
    front_waist_minus_pleat = front_waist_curve_len - 3.5  # pleat = 3.5 cm
    front_waist_transfer_pt = back_cb_waist + waist_unit * front_waist_minus_pleat
    # Sideseam intake is given (1–1.5 cm); dart total is derived to balance:
    #   ½ Wbg + dart_total + sideseam_intake = back_waist + front_waist_minus_pleat
    half_Wbg = Wbg / 2
    total_available = waist_len + front_waist_minus_pleat
    dart_total = total_available - half_Wbg - SIDESEAM_INTAKE
    # Split into two darts
    dart_large = dart_total * DART_LARGE_RATIO
    dart_small = dart_total - dart_large
    # Verification: ½ Wbg + darts from transfer pt to the left → remaining = intake
    half_Wbg_plus_darts = half_Wbg + dart_total
    check_pt = front_waist_transfer_pt - waist_unit * half_Wbg_plus_darts

    # Dart positions along waistline
    # Smaller dart at 1/4 from sideseam, larger at 1/2 waistline
    dart1_center = back_waist_side + waist_unit * (waist_len / 4)
    dart2_center = back_waist_side + waist_unit * (waist_len / 2)

    # Dart perpendicular: "Square down for each dart centre line."
    # Perpendicular to waistline, pointing downward.
    dart_perp = np.array([waist_unit[1], -waist_unit[0]])
    if dart_perp[1] > 0:
        dart_perp = -dart_perp

    # Dart edges spread along the waistline (±½ intake from centre)
    # "left" = toward sideseam, "right" = toward CB
    dart1_left  = dart1_center - waist_unit * (dart_small / 2)
    dart1_right = dart1_center + waist_unit * (dart_small / 2)
    dart1_tip   = dart1_center + dart_perp * DART_SMALL_LEN

    dart2_left  = dart2_center - waist_unit * (dart_large / 2)
    dart2_right = dart2_center + waist_unit * (dart_large / 2)
    dart2_tip   = dart2_center + dart_perp * DART_LARGE_LEN

    # ================================================================
    # Step 6: Final Curves and Outline
    # ================================================================

    # -- Inseam curve: knee → crotch point --
    # "Draw the inseam in a slightly curved from the knee line to the
    # marked crotch point."
    # Control point biased toward crotch end → straight at knee, curves near crotch
    inseam_ctrl = 0.2 * back_knee_inseam + 0.8 * back_crotch_pt
    curve_inseam = _bezier_quad(
        back_knee_inseam,
        inseam_ctrl + np.array([-1.5, 0.0]),
        back_crotch_pt,
    )

    # -- Crotch curve: bcw_mark → back_crotch_pt --
    # Deeper curve than front for the wider seat.
    # Starts heading downward from bcw_mark, sweeps out to crotch point.
    crotch_span_y = bcw_mark[1] - back_crotch_pt[1]
    crotch_span_x = back_crotch_pt[0] - bcw_mark[0]
    curve_crotch = _bezier_cubic(
        bcw_mark,
        bcw_mark + np.array([crotch_span_x * 0.1, -crotch_span_y * 0.6]),
        back_crotch_pt + np.array([-crotch_span_x * 0.4, 0.0]),
        back_crotch_pt,
    )

    # -- CB line: back_cb_waist → bcw_mark (straight along CB direction) --

    # -- Sideseam lower: knee → hip --
    # "Starting from the knee line, draw the sideseam first slightly
    # hollow..."  (hollow = slight concavity toward pattern interior)
    # Control point biased toward hip end → straight at knee, hollows near hip
    side_lower_ctrl = 0.3 * back_knee_side + 0.7 * back_hip_side
    curve_side_lower = _bezier_quad(
        back_knee_side,
        side_lower_ctrl + np.array([0.8, 0.0]),
        back_hip_side,
    )

    # -- Sideseam intake at waist --
    # The sideseam is taken in 1–1.5 cm at the waist.  The actual
    # waist/sideseam junction is inward along the waistline.
    waist_intake_pt = back_waist_side + waist_unit * SIDESEAM_INTAKE

    # -- Sideseam upper: hip → waist intake point --
    # "...and then curved over the hipline upwards to the marked point
    # at the waistline."
    curve_side_upper = _bezier_quad(
        back_hip_side,
        (back_hip_side + waist_intake_pt) / 2 + np.array([-0.5, 0.0]),
        waist_intake_pt,
    )

    # -- Waistline: slightly curved between the darts --
    # Three segments: intake_pt→dart1_left, dart1_right→dart2_left,
    # dart2_right→cb_waist.  Middle segment dips slightly.
    curve_waist_seg1 = np.array([waist_intake_pt, dart1_left])
    mid_between = (dart1_right + dart2_left) / 2
    curve_waist_seg2 = _bezier_quad(
        dart1_right,
        mid_between + dart_perp * 0.3,    # slight dip between darts
        dart2_left,
    )
    curve_waist_seg3 = np.array([dart2_right, back_cb_waist])

    # -- Verification: perpendicular from CB to sideseam/hipline --
    # "Draw a perpendicular line from the centre back to the intersection
    # of the sideseam and the hipline."
    # Should be approximately ¼ Hg + 2.5–3.5 cm.
    verif_dist = np.linalg.norm(back_hip_side - bcw_mark)
    verif_expected = Hg / 4 + 3.0

    # ================================================================
    # Hip Measurement Verification (MM&S)
    # ================================================================
    # A = front hipline (sideseam → CF), B = back (CB⊥ → sideseam/hip)
    # A + B − ½ Hg = ½ ease.  Expect ~4–5 cm for classic fit.
    A_front = abs(fpts['cf_hip'][0] - fpts['hip_side'][0])
    v_hip = back_hip_side - bcw_mark
    par = np.dot(v_hip, cb_perp_unit) * cb_perp_unit
    B_back = np.linalg.norm(v_hip - par)
    half_ease = A_front + B_back - Hg / 2

    if half_ease < 3.5:
        print(f"WARNING: ½ ease = {half_ease:.1f} cm (A={A_front:.1f} + B={B_back:.1f} "
              f"− ½Hg={Hg/2:.1f}). Expected ≥ 3.5 cm for classic fit.")
    elif half_ease > 5.5:
        print(f"WARNING: ½ ease = {half_ease:.1f} cm (A={A_front:.1f} + B={B_back:.1f} "
              f"− ½Hg={Hg/2:.1f}). Expected ≤ 5.5 cm — pattern may be too loose.")
    else:
        print(f"Hip verification OK: ½ ease = {half_ease:.1f} cm "
              f"(A={A_front:.1f} + B={B_back:.1f} − ½Hg={Hg/2:.1f})")

    # ================================================================
    # Seam Transition Checks (MM&S)
    # ================================================================
    # 1) "Join the front and back trouser patterns at the inseam and
    #     check the seam transition at the crotch line."
    # 2) "Join the front and back trouser patterns at the sideseam and
    #     check the seam transition at the waistline."
    # We measure the kink angle at each knee join point: 0° = smooth.

    def _tangent_angle(curve, end='start', n=3):
        """Tangent angle (degrees) at start or end of a curve."""
        if end == 'start':
            d = curve[n] - curve[0]
        else:
            d = curve[-1] - curve[-n - 1]
        return np.degrees(np.arctan2(d[1], d[0]))

    def _kink(angle_a, angle_b):
        """Kink between two tangent angles that should be ~180° apart."""
        diff = abs(angle_a - angle_b)
        return abs(180 - diff) if diff < 360 else abs(diff - 360)

    KINK_WARN = 10.0  # degrees

    # Inseam: front inseam_upper arrives at knee, back inseam departs from knee
    inseam_front_angle = _tangent_angle(front['curves']['inseam_upper'], 'end')
    inseam_back_angle = _tangent_angle(curve_inseam, 'start')
    inseam_kink = _kink(inseam_front_angle, inseam_back_angle)

    if inseam_kink > KINK_WARN:
        print(f"WARNING: Inseam kink at knee = {inseam_kink:.1f}° (> {KINK_WARN}°). "
              f"Blend the seam transition at the crotch line.")
    else:
        print(f"Inseam join OK: kink = {inseam_kink:.1f}°")

    # Sideseam: front side_upper arrives at knee, back side_lower departs from knee
    side_front_angle = _tangent_angle(front['curves']['side_upper'], 'end')
    side_back_angle = _tangent_angle(curve_side_lower, 'start')
    side_kink = _kink(side_front_angle, side_back_angle)

    if side_kink > KINK_WARN:
        print(f"WARNING: Sideseam kink at knee = {side_kink:.1f}° (> {KINK_WARN}°). "
              f"Blend the seam transition at the waistline.")
    else:
        print(f"Sideseam join OK: kink = {side_kink:.1f}°")

    # -- Collect everything --
    points = {
        'back_hem_side':      back_hem_side,
        'back_hem_side_top':  back_hem_side_top,
        'back_hem_inseam':    back_hem_inseam,
        'back_hem_inseam_top': back_hem_inseam_top,
        'back_knee_side':     back_knee_side,
        'back_knee_inseam':   back_knee_inseam,
        'back_hip_side':      back_hip_side,
        'back_hip_inseam':    back_hip_inseam,
        'bcw_mark':           bcw_mark,
        'back_crotch_pt':     back_crotch_pt,
        'cb_slant_origin':    cb_slant_origin,
        'back_waist_side':    back_waist_side,
        'waist_intake_pt':    waist_intake_pt,
        'back_cb_waist':      back_cb_waist,
        'dart1_left':         dart1_left,
        'dart1_right':        dart1_right,
        'dart1_tip':          dart1_tip,
        'dart2_left':         dart2_left,
        'dart2_right':        dart2_right,
        'dart2_tip':          dart2_tip,
        'front_waist_transfer_pt': front_waist_transfer_pt,
        'waist_check_pt':         check_pt,
    }

    levels = front['levels']  # shared

    construction = {
        'back_creaseline_x':  back_creaseline_x,
        'width_center_x':     width_center_x,
        'half_Tbtw':          half_Tbtw,
        'cb_perp_unit':       cb_perp_unit,
        'verif_dist':         verif_dist,
        'verif_expected':     verif_expected,
        # Step 4 intermediate values for visualization
        'front_inseam_len':   front_inseam_len,
        'back_inseam_target': back_inseam_target,
        'front_side_from_knee': front_side_from_knee,
        'back_creaseline_knee': back_creaseline_knee,
        'waist_side_height':  waist_side_height,
        'cb_height_extra':    CB_HEIGHT_EXTRA,
        # Step 5 waist verification
        'front_waist_minus_pleat': front_waist_minus_pleat,
        'half_Wbg':           half_Wbg,
        'half_Wbg_plus_darts': half_Wbg_plus_darts,
        'dart_total':         dart_total,
        'sideseam_intake':    SIDESEAM_INTAKE,
        # Hip verification
        'A_front':            A_front,
        'B_back':             B_back,
        'half_ease':          half_ease,
        # Seam transition checks
        'inseam_kink':        inseam_kink,
        'side_kink':          side_kink,
    }

    curves = {
        'inseam':      curve_inseam,
        'crotch':      curve_crotch,
        'side_lower':  curve_side_lower,
        'side_upper':  curve_side_upper,
        'waist_seg1':  curve_waist_seg1,
        'waist_seg2':  curve_waist_seg2,
        'waist_seg3':  curve_waist_seg3,
    }

    measurements = {
        'Tbtw': Tbtw,
        'Btw': Btw,
        'Bcw': Bcw,
    }

    return {
        'points': points,
        'levels': levels,
        'construction': construction,
        'curves': curves,
        'measurements': measurements,
        'metadata': {'title': '1-Pleat Trouser Back (MM&S)'},
    }


# -- Visualization -----------------------------------------------------------

def _draw_front_faded(ax, front, x_max):
    """Draw the front panel faded as reference."""
    FADED = dict(color='silver', linewidth=1.0, alpha=0.2, zorder=1)
    fpts = front['points']
    fcrv = front['curves']

    # Outline curves
    for crv in fcrv.values():
        ax.plot(crv[:, 0], crv[:, 1], **FADED)

    # Straight segments
    segments = [
        ('cf_waist', 'cf_hip'),
        ('mid_side', 'hip_side'),
        ('knee_inseam', 'hem_inseam_top'),
        ('knee_side', 'hem_side_top'),
    ]
    for a, b in segments:
        ax.plot([fpts[a][0], fpts[b][0]], [fpts[a][1], fpts[b][1]], **FADED)

    # Hem
    ax.plot([fpts['hem_inseam_top'][0], fpts['hem_inseam'][0],
             fpts['hem_side'][0], fpts['hem_side_top'][0]],
            [fpts['hem_inseam_top'][1], fpts['hem_inseam'][1],
             fpts['hem_side'][1], fpts['hem_side_top'][1]], **FADED)

    # Pleat symbol faded
    con = front['construction']
    lvl = front['levels']
    pr = con['creaseline_x']
    pl = con['pleat_x']
    pm = (pr + pl) / 2
    py = front['levels']['waistline']
    chev_h = 1.5
    drop = 6.0
    PLEAT_FADED = dict(color='silver', linewidth=0.6, alpha=0.15)
    ax.plot([pl, pl], [py, py - drop], **PLEAT_FADED)
    ax.plot([pr, pr], [py, py - drop], **PLEAT_FADED)
    ax.plot([pl, pm, pr], [py - 0.5, py - 0.5 - chev_h, py - 0.5], **PLEAT_FADED)
    ax.plot([pl, pm, pr],
            [py - 0.5 - chev_h, py - 0.5 - 2 * chev_h, py - 0.5 - chev_h], **PLEAT_FADED)


def plot_trouser_back(front, back, output_path='Logs/trouser_back.svg',
                      debug=False, units='cm', step=6):
    """Render the trouser back draft up to the given step (1-6).

    Front panel is drawn faded; back panel in bold black.
    """
    bpts = back['points']
    bcon = back['construction']
    bcrv = back['curves']
    lvl  = back['levels']

    fig, ax = plt.subplots(1, 1, figsize=(10, 16))
    plt.rcParams['lines.solid_capstyle'] = 'butt'
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
    CON = dict(color='cornflowerblue', linewidth=0.6, linestyle=':', alpha=0.5)
    OUTLINE = dict(color='black', linewidth=1.5, zorder=4)

    x_max = bpts['back_hip_inseam'][0] + 5

    # -- Front faded (always shown) --
    _draw_front_faded(ax, front, x_max)

    # -- Horizontal reference lines (shared from front) --
    for name, y in lvl.items():
        ax.plot([-8, x_max], [y, y], **REF)
        ax.annotate(name, (x_max, y), textcoords='offset points',
                    xytext=(4, 2), fontsize=7, color='gray')

    # ── Step 1: Extend Legs + Back Creaseline + CB Slant ───────────
    # Extended leg points
    for pt_name in ('back_knee_side', 'back_hem_side_top', 'back_hem_side',
                    'back_knee_inseam', 'back_hem_inseam_top', 'back_hem_inseam'):
        ax.plot(*bpts[pt_name], 'ko', markersize=3)

    # Extended leg lines (full outline: knee → hem_top → hem → hem → hem_top → knee)
    EXT = dict(color='black', linewidth=0.8, alpha=0.5)
    ax.plot([bpts['back_knee_side'][0], bpts['back_hem_side_top'][0],
             bpts['back_hem_side'][0], bpts['back_hem_inseam'][0],
             bpts['back_hem_inseam_top'][0], bpts['back_knee_inseam'][0]],
            [bpts['back_knee_side'][1], bpts['back_hem_side_top'][1],
             bpts['back_hem_side'][1], bpts['back_hem_inseam'][1],
             bpts['back_hem_inseam_top'][1], bpts['back_knee_inseam'][1]],
            **EXT)

    # Back creaseline = front creaseline (grainline, unchanged)
    ax.plot([bcon['back_creaseline_x'], bcon['back_creaseline_x']],
            [-3, lvl['waistline'] + 5],
            'k-.', linewidth=0.6, alpha=0.4)
    ax.annotate('back creaseline', (bcon['back_creaseline_x'], -3),
                fontsize=7, color='black', ha='center', va='top')
    # Construction mark: 1–1.5 cm to the right on hipline (width distribution centre)
    ax.plot(bcon['width_center_x'], lvl['hipline'], 'ko', markersize=4)
    ax.annotate('1\u20131.5', (bcon['width_center_x'], lvl['hipline']),
                textcoords='offset points', xytext=(6, -8),
                fontsize=6, color='black')

    # CB slant origin
    ax.plot(*bpts['cb_slant_origin'], 'o', color='cornflowerblue', markersize=4)
    ax.annotate('CB slant', bpts['cb_slant_origin'], textcoords='offset points',
                xytext=(-10, 6), fontsize=5, color='cornflowerblue')

    if step < 2:
        _finish_back_plot(fig, ax, back, output_path, step)
        return

    # ── Step 2: Width Distribution on Hipline ──────────────────────
    # ½ Tbtw left and right from width centre; Bcw back to the left
    ax.plot(*bpts['back_hip_side'], 'ko', markersize=4)
    ax.plot(*bpts['back_hip_inseam'], 'ko', markersize=4)
    ax.plot(*bpts['bcw_mark'], 's', color='cornflowerblue', markersize=4)

    ax.annotate('back hip (side)', bpts['back_hip_side'], textcoords='offset points',
                xytext=(-10, 6), fontsize=5, color='black')
    ax.annotate('back hip (inseam)', bpts['back_hip_inseam'], textcoords='offset points',
                xytext=(4, 6), fontsize=5, color='black')
    ax.annotate('CB/hip', bpts['bcw_mark'], textcoords='offset points',
                xytext=(4, -10), fontsize=5, color='cornflowerblue')

    # Tbtw dimension arrow
    ax.annotate('', xy=(bpts['back_hip_side'][0], lvl['hipline'] + 1.5),
                xytext=(bpts['back_hip_inseam'][0], lvl['hipline'] + 1.5),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=0.6))
    ax.text(bcon['width_center_x'], lvl['hipline'] + 3,
            f"Tbtw={back['measurements']['Tbtw']:.1f}", fontsize=6,
            color='blue', ha='center')

    if step < 3:
        _finish_back_plot(fig, ax, back, output_path, step)
        return

    # ── Step 3: Connect Knee to Hip + CB Direction ─────────────────
    # Sideseam guideline: knee → hip
    ax.plot([bpts['back_knee_side'][0], bpts['back_hip_side'][0]],
            [bpts['back_knee_side'][1], bpts['back_hip_side'][1]],
            'k-', linewidth=0.5, alpha=0.4)
    # Inseam guideline: knee → hip
    ax.plot([bpts['back_knee_inseam'][0], bpts['back_hip_inseam'][0]],
            [bpts['back_knee_inseam'][1], bpts['back_hip_inseam'][1]],
            'k-', linewidth=0.5, alpha=0.4)
    # CB guideline: slant origin → bcw_mark and beyond
    cb_ext = bpts['bcw_mark'] + bcon['cb_perp_unit'] * 20
    ax.plot([bpts['cb_slant_origin'][0], bpts['bcw_mark'][0], cb_ext[0]],
            [bpts['cb_slant_origin'][1], bpts['bcw_mark'][1], cb_ext[1]],
            color='cornflowerblue', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.annotate('CB', (cb_ext[0], cb_ext[1]), textcoords='offset points',
                xytext=(4, 4), fontsize=7, fontweight='bold', color='cornflowerblue')

    if step < 4:
        _finish_back_plot(fig, ax, back, output_path, step)
        return

    # ── Step 4: Transfer Lengths + Waist Heights ───────────────────

    # (a) Back crotch point — inseam length transfer (front inseam − 0.7)
    ax.plot(*bpts['back_crotch_pt'], 'ko', markersize=4)
    ax.annotate(f"inseam {bcon['back_inseam_target']:.1f}\n(front {bcon['front_inseam_len']:.1f} \u2212 0.7)",
                bpts['back_crotch_pt'], textcoords='offset points',
                xytext=(6, -6), fontsize=5, color='black')

    # (b) Extend sideseam guideline upward past hip → back_waist_side
    ax.plot([bpts['back_hip_side'][0], bpts['back_waist_side'][0]],
            [bpts['back_hip_side'][1], bpts['back_waist_side'][1]],
            'k-', linewidth=0.5, alpha=0.4)
    ax.plot(*bpts['back_waist_side'], 'ko', markersize=4)
    ax.annotate(f"sideseam {bcon['front_side_from_knee']:.1f}\n(from knee)",
                bpts['back_waist_side'], textcoords='offset points',
                xytext=(-12, 6), fontsize=5, color='black', ha='right')

    # (c) CB waist height: knee centre → waist_side, then transfer + 0–1 cm along CB
    back_cl_knee = bcon['back_creaseline_knee']

    # Intermediate line: back creaseline @ knee → back_waist_side (the measurement)
    ax.plot([back_cl_knee[0], bpts['back_waist_side'][0]],
            [back_cl_knee[1], bpts['back_waist_side'][1]],
            color='cornflowerblue', linewidth=0.8, linestyle='--', alpha=0.5)
    mid_meas = (back_cl_knee + bpts['back_waist_side']) / 2
    ax.annotate(f"{bcon['waist_side_height']:.1f}",
                mid_meas, textcoords='offset points',
                xytext=(6, 0), fontsize=6, color='cornflowerblue', ha='left')
    ax.plot(*back_cl_knee, '+', color='cornflowerblue', markersize=5)

    # Transfer that distance + 0–1 cm upward along CB from knee
    ax.plot([back_cl_knee[0], bpts['back_cb_waist'][0]],
            [back_cl_knee[1], bpts['back_cb_waist'][1]],
            color='cornflowerblue', linewidth=0.6, linestyle=':', alpha=0.5)
    ax.plot(*bpts['back_cb_waist'], 'ko', markersize=4)
    ax.annotate(f"{bcon['waist_side_height']:.1f} + {bcon['cb_height_extra']:.1f}",
                bpts['back_cb_waist'], textcoords='offset points',
                xytext=(6, 6), fontsize=5, color='black')

    if step < 5:
        _finish_back_plot(fig, ax, back, output_path, step)
        return

    # ── Step 5: Waistline + Darts ──────────────────────────────────
    # Waistline (construction straight line, extended past CB)
    waist_unit = (bpts['back_cb_waist'] - bpts['back_waist_side'])
    waist_unit = waist_unit / np.linalg.norm(waist_unit)
    waist_ext = bpts['back_cb_waist'] + waist_unit * 5  # extend past CB
    ax.plot([bpts['back_waist_side'][0], waist_ext[0]],
            [bpts['back_waist_side'][1], waist_ext[1]],
            'k-', linewidth=0.5, alpha=0.3)

    # Front waist minus pleat: transferred from CB to the right
    fwt = bpts['front_waist_transfer_pt']
    ax.plot([bpts['back_cb_waist'][0], fwt[0]],
            [bpts['back_cb_waist'][1], fwt[1]],
            'k--', linewidth=0.8, alpha=0.4)
    ax.plot(*fwt, '|', color='black', markersize=8, markeredgewidth=1.5)
    ax.annotate(f"front waist \u2212 pleat\n{bcon['front_waist_minus_pleat']:.1f}",
                fwt, textcoords='offset points',
                xytext=(6, -10), fontsize=5, color='black', ha='left')

    # From transfer point, ½ Wbg + darts to the left (toward sideseam)
    chk = bpts['waist_check_pt']
    ax.plot(*chk, '|', color='cornflowerblue', markersize=8, markeredgewidth=1.5)
    ax.annotate(f"\u00bd Wbg + darts\n{bcon['half_Wbg']:.0f} + {bcon['dart_total']:.1f}",
                chk, textcoords='offset points',
                xytext=(0, 10), fontsize=5, color='cornflowerblue', ha='center')

    # Remaining = sideseam intake (distance from check_pt to sideseam)
    intake = bcon['sideseam_intake']
    ax.annotate(f"remaining {intake:.1f}\n(expect 1\u20131.5)",
                bpts['back_waist_side'], textcoords='offset points',
                xytext=(-12, -10), fontsize=5,
                color='red' if intake < 0.8 else 'darkgreen', ha='right')

    # Darts
    DART_STYLE = dict(color='black', linewidth=1.0, zorder=4)
    # Small dart (2.0 cm, 7.5 cm)
    ax.plot([bpts['dart1_left'][0], bpts['dart1_tip'][0], bpts['dart1_right'][0]],
            [bpts['dart1_left'][1], bpts['dart1_tip'][1], bpts['dart1_right'][1]],
            **DART_STYLE)
    # Large dart (2.5 cm, 9.5 cm)
    ax.plot([bpts['dart2_left'][0], bpts['dart2_tip'][0], bpts['dart2_right'][0]],
            [bpts['dart2_left'][1], bpts['dart2_tip'][1], bpts['dart2_right'][1]],
            **DART_STYLE)

    if step < 6:
        _finish_back_plot(fig, ax, back, output_path, step)
        return

    # ── Step 6: Final Curves and Outline ───────────────────────────

    # CB line: back_cb_waist → bcw_mark (straight)
    ax.plot([bpts['back_cb_waist'][0], bpts['bcw_mark'][0]],
            [bpts['back_cb_waist'][1], bpts['bcw_mark'][1]], **OUTLINE)

    # Crotch curve: bcw_mark → back_crotch_pt
    ax.plot(bcrv['crotch'][:, 0], bcrv['crotch'][:, 1], **OUTLINE)

    # Inseam curve: knee → crotch point
    ax.plot(bcrv['inseam'][:, 0], bcrv['inseam'][:, 1], **OUTLINE)

    # Inseam lower: knee → hem_inseam_top (straight)
    ax.plot([bpts['back_knee_inseam'][0], bpts['back_hem_inseam_top'][0]],
            [bpts['back_knee_inseam'][1], bpts['back_hem_inseam_top'][1]], **OUTLINE)

    # Hem: perpendicular returns + hemline (butt cap)
    ax.plot([bpts['back_hem_inseam_top'][0], bpts['back_hem_inseam'][0],
             bpts['back_hem_side'][0], bpts['back_hem_side_top'][0]],
            [bpts['back_hem_inseam_top'][1], bpts['back_hem_inseam'][1],
             bpts['back_hem_side'][1], bpts['back_hem_side_top'][1]],
            **OUTLINE, solid_capstyle='butt')

    # Sideseam lower: hem_side_top → knee_side (straight)
    ax.plot([bpts['back_hem_side_top'][0], bpts['back_knee_side'][0]],
            [bpts['back_hem_side_top'][1], bpts['back_knee_side'][1]], **OUTLINE)

    # Sideseam: knee → hip (slightly hollow curve)
    ax.plot(bcrv['side_lower'][:, 0], bcrv['side_lower'][:, 1], **OUTLINE)

    # Sideseam upper: hip → waist (curved over hipline)
    ax.plot(bcrv['side_upper'][:, 0], bcrv['side_upper'][:, 1], **OUTLINE)

    # Waistline: three segments (straight, curved between darts, straight)
    ax.plot(bcrv['waist_seg1'][:, 0], bcrv['waist_seg1'][:, 1], **OUTLINE)
    ax.plot(bcrv['waist_seg2'][:, 0], bcrv['waist_seg2'][:, 1], **OUTLINE)
    ax.plot(bcrv['waist_seg3'][:, 0], bcrv['waist_seg3'][:, 1], **OUTLINE)

    # Verification line: perpendicular from CB to sideseam/hipline
    VERIF = dict(color='darkgreen', linewidth=0.8, linestyle='--', alpha=0.6)
    ax.plot([bpts['bcw_mark'][0], bpts['back_hip_side'][0]],
            [bpts['bcw_mark'][1], bpts['back_hip_side'][1]], **VERIF)
    verif = bcon['verif_dist']
    expected = bcon['verif_expected']
    mid_verif = (bpts['bcw_mark'] + bpts['back_hip_side']) / 2
    ax.annotate(f"{verif:.1f} (\u00bc Hg + 3 \u2248 {expected:.1f})",
                mid_verif, textcoords='offset points',
                xytext=(0, -8), fontsize=6, color='darkgreen', ha='center')

    # -- Debug: dimension annotations --
    if debug:
        _annotate_len(ax, bcrv['crotch'], offset=(6, 6))
        _annotate_len(ax, bcrv['inseam'], offset=(8, 0))
        _annotate_len(ax, bcrv['side_lower'], offset=(-10, 0), label='side lo')
        _annotate_len(ax, bcrv['side_upper'], offset=(-10, 0), label='side up')
        _annotate_len(ax, bcrv['waist_seg2'], offset=(0, 8))
        _annotate_len(ax, np.array([bpts['back_cb_waist'], bpts['bcw_mark']]),
                      offset=(6, 0), label='CB')
        _annotate_len(ax, np.array([bpts['back_knee_inseam'], bpts['back_hem_inseam_top']]),
                      offset=(8, 0))
        _annotate_len(ax, np.array([bpts['back_hem_side_top'], bpts['back_knee_side']]),
                      offset=(-10, 0))
        _annotate_len(ax, np.array([bpts['back_hem_side'], bpts['back_hem_inseam']]),
                      offset=(0, -8))

    _finish_back_plot(fig, ax, back, output_path, step)


def _finish_back_plot(fig, ax, back, output_path, step):
    """Common plot finalization."""
    title = f"{back['metadata']['title']} — Step {step}"
    ax.set_title(title)
    ax.set_aspect('equal')
    ax.margins(0.05)
    ax.grid(True, alpha=0.15)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {output_path}")


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm'):
    """Uniform interface called by the generic runner."""
    m = load_measurements(measurements_path)
    front = draft_trouser_front(m)
    back = draft_trouser_back(m, front)

    out = Path(output_path)
    stem = out.stem
    suffix = out.suffix or '.svg'
    parent = out.parent

    # Per-step SVGs
    for s in range(1, 7):
        step_path = parent / f"{stem}_step{s}{suffix}"
        plot_trouser_back(front, back, str(step_path), debug=debug, units=units, step=s)

    # Final output at the requested path
    plot_trouser_back(front, back, output_path, debug=debug, units=units, step=6)
