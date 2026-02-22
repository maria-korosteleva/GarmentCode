"""
1-Pleat Trouser Front Panel (MM&S Basic Block)

Based on: MM&S - Basic Block: Trousers with 1 Pleat - Front Pattern

Coordinate system:
  - Origin A at bottom-left (hemline, left reference edge)
  - X axis: positive to the right
  - Y axis: positive upward
"""
import yaml
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

INCH = 2.54  # cm per inch


def load_measurements(yaml_path):
    """Load measurements from YAML, converting inches to cm if needed."""
    with open(yaml_path) as f:
        raw = yaml.safe_load(f)['measurements']
    unit = raw.get('unit', 'inch')
    scale = INCH if unit == 'inch' else 1.0
    m = {}
    for key, val in raw.items():
        if key == 'unit':
            continue
        m[key] = val * scale
    return m


# -- Bezier helpers ----------------------------------------------------------

def _bezier_cubic(P0, P1, P2, P3, n=100):
    t = np.linspace(0, 1, n).reshape(-1, 1)
    return (1-t)**3 * P0 + 3*(1-t)**2 * t * P1 + 3*(1-t) * t**2 * P2 + t**3 * P3


def _bezier_quad(P0, P1, P2, n=100):
    t = np.linspace(0, 1, n).reshape(-1, 1)
    return (1-t)**2 * P0 + 2*(1-t) * t * P1 + t**2 * P2


def _curve_length(pts):
    """Arc length of a polyline (Nx2 array)."""
    diffs = np.diff(pts, axis=0)
    return np.sum(np.sqrt(diffs[:, 0]**2 + diffs[:, 1]**2))


def _annotate_len(ax, pts, offset=(0, 6), label=None):
    """Label a polyline/curve with its arc length at the midpoint."""
    length = _curve_length(np.atleast_2d(pts))
    mid = pts[len(pts) // 2]
    text = f'{length:.1f}' if label is None else f'{label} {length:.1f}'
    ax.annotate(text, mid, textcoords='offset points',
                xytext=offset, fontsize=6, color='darkblue', ha='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))


# -- Drafting ----------------------------------------------------------------

def draft_trouser_front(m):
    """
    Compute all geometry for the 1-pleat trouser front.

    Parameters
    ----------
    m : dict  Measurements in cm.

    Returns
    -------
    dict with keys: points, levels, construction, curves, measurements, metadata
    """
    # -- Extract measurements --
    Wbg = m['waist']        # waistband girth (full circumference)
    Hg  = m['seat']         # hip girth (full circumference)
    Hw  = m['hem_width']    # hem width (full circumference)
    Sl  = m['side_length']  # side length (waist to floor)
    Is  = m['inseam']       # inseam (crotch to floor)

    # -- Derived measurements --
    Br  = Sl - Is                     # body rise
    Kh  = Is / 2 + Is / 10 - 2.0     # knee height
    Ftw = Hg / 4 + 1.0               # front trouser width
    Fcw = Hg / 2 / 10 + 1.0          # front crotch width
    Cw  = Hg / 4 - 4.0               # crotch width (total)
    Bcw = Cw - Fcw                    # back crotch width
    Btw = Hg / 4 + 3.5               # back trouser width (midpoint of +3 to +4 range)

    # ==========================================================
    # Step 1: Framework — vertical + horizontal reference lines
    # ==========================================================
    hem_y    = 0.0
    knee_y   = Kh
    crotch_y = Is
    hip_rise = Hg / 2 / 10 + 3.0     # 1/10 of 1/2 Hg + 3 cm above crotch
    hip_y    = crotch_y + hip_rise
    waist_y  = Sl

    # ==========================================================
    # Step 2: Widths and creaseline
    # ==========================================================
    ftw_x        = Ftw                 # Ftw perpendicular on hipline
    fcw_mark_x   = Ftw + Fcw          # Fcw construction mark (total front width)
    creaseline_x = fcw_mark_x / 2     # midpoint: front creaseline / grainline
    mid_hip_crotch_y = (hip_y + crotch_y) / 2

    # ==========================================================
    # Step 3: Hem widths, pleat, CF
    # ==========================================================
    hem_half = Hw / 4 - 1.0           # each side of creaseline
    hem_side_x   = creaseline_x - hem_half
    hem_inseam_x = creaseline_x + hem_half

    # 0.5 cm inward from each hem edge → sideseam/inseam guidelines
    hem_side_guide_x   = hem_side_x + 0.5
    hem_inseam_guide_x = hem_inseam_x - 0.5

    # Pleat: 3.5 cm left of creaseline on waistline
    pleat_x = creaseline_x - 3.5

    # Centre front (CF): Ftw + 0.5 on hipline, angled to Ftw at waistline
    cf_hip_x   = Ftw + 0.5   # 0.5 cm ease at hip
    cf_waist_x = Ftw          # CF at waist sits on the Ftw perpendicular

    # Inseam guideline: from hem_inseam_guide to Fcw mark on hipline
    # The actual crotch point is where this inseam line crosses the crotch line.
    inseam_target = np.array([fcw_mark_x, hip_y])
    inseam_origin = np.array([hem_inseam_guide_x, hem_y])
    t_crotch = (crotch_y - hem_y) / (hip_y - hem_y)
    crotch_pt_x = hem_inseam_guide_x + t_crotch * (fcw_mark_x - hem_inseam_guide_x)
    crotch_pt = np.array([crotch_pt_x, crotch_y])

    # ==========================================================
    # Step 4: Shaping
    # ==========================================================
    # Knee points: intersect sideseam guideline at knee line, then taper 1 cm out.
    # Sideseam guideline: hem_side_guide (hem_side_guide_x, 0) → mid_side (0, mid_hip_crotch_y)
    t_knee_side = (knee_y - hem_y) / (mid_hip_crotch_y - hem_y)
    knee_side_on_guide = hem_side_guide_x + t_knee_side * (0.0 - hem_side_guide_x)
    knee_side_x   = knee_side_on_guide + 1.0  # 1 cm inward (toward creaseline)
    # Measure to creaseline and transfer to the right
    knee_side_dist = creaseline_x - knee_side_x
    knee_inseam_x = creaseline_x + knee_side_dist

    # CF direction (waist→hip, continuing downward)
    cf_dir = np.array([cf_hip_x - cf_waist_x, hip_y - waist_y])
    # Find where CF crosses the crotch line
    t_cf_crotch = (crotch_y - waist_y) / cf_dir[1]
    cf_at_crotch = np.array([cf_waist_x + t_cf_crotch * cf_dir[0], crotch_y])

    # Crotch guide: half the distance from CF@crotch to crotch_pt,
    # transferred upward from CF@crotch
    half_crotch_dist = (crotch_pt_x - cf_at_crotch[0]) / 2
    crotch_guide = np.array([cf_at_crotch[0], crotch_y + half_crotch_dist])

    # Slanted line from crotch guide to crotch point (construction reference)
    # CF goes straight to crotch line; the crotch curve starts there and
    # bows toward the crotch guide line.

    # Waist sideseam: 1/4 Wbg + 3.5 (pleat) = 25.5 from CF gives a natural
    # intake of (cf_waist_x - 25.5) from the hip sideseam.  The -1.5 relocates
    # the sideseam: the front only takes 1.5 cm of intake; the back adds the
    # remaining 1.5 cm on its side.
    sideseam_relocation = 1.5
    waist_side_x = sideseam_relocation

    # ==========================================================
    # Step 5: Final curves
    # ==========================================================
    # Raise waistline 0.7 cm at sideseam
    waist_side_raised = np.array([waist_side_x, waist_y + 0.7])

    # Key outline points
    hem_side   = np.array([hem_side_x, hem_y])
    hem_inseam = np.array([hem_inseam_x, hem_y])
    hem_perp   = 4.0  # cm perpendicular at hem edge
    hem_side_top   = np.array([hem_side_x, hem_y + hem_perp])
    hem_inseam_top = np.array([hem_inseam_x, hem_y + hem_perp])
    knee_side  = np.array([knee_side_x, knee_y])
    knee_inseam = np.array([knee_inseam_x, knee_y])
    mid_side   = np.array([0.0, mid_hip_crotch_y])  # sideseam at x=0
    hip_side   = np.array([0.0, hip_y])              # sideseam at hipline
    cf_waist   = np.array([cf_waist_x, waist_y])
    cf_hip     = np.array([cf_hip_x, hip_y])
    pleat_pt   = np.array([pleat_x, waist_y])

    # -- Waistline curve: waist_side_raised → cf_waist --
    # Slightly curved inward (dips below the straight line) from sideseam
    # to around the pleat, then levels out to CF.
    waist_span = cf_waist_x - waist_side_x
    waist_dip = 0.5  # cm inward (downward)
    curve_waistline = _bezier_cubic(
        waist_side_raised,
        waist_side_raised + np.array([waist_span / 3, -waist_dip]),
        cf_waist + np.array([-waist_span / 3, 0.0]),
        cf_waist,
    )

    # -- Hip curve: hip_side → waist_side_raised --
    # Gentle C-curve; single control point (quadratic) guarantees no S-shape.
    hip_mid = (hip_side + waist_side_raised) / 2
    curve_hip = _bezier_quad(
        hip_side,
        hip_mid + np.array([-0.3, 0.0]),   # slight inward bow
        waist_side_raised,
    )

    # -- Crotch curve: cf_hip → crotch_pt --
    # Starts at CF on the hipline, sweeps as a shallow curve down to the
    # crotch point.  P2 follows the slant direction (crotch_pt → crotch_guide)
    # so the curve stays above the guide line.
    crotch_span_y = cf_hip[1] - crotch_pt[1]
    slant_dir = crotch_guide - crotch_pt
    slant_len = np.linalg.norm(slant_dir)
    slant_unit = slant_dir / slant_len
    curve_crotch = _bezier_cubic(
        cf_hip,
        cf_hip + np.array([0.0, -crotch_span_y / 2]),
        crotch_pt + slant_unit * (slant_len / 2),
        crotch_pt,
    )

    # -- Inseam upper: crotch_pt → knee_inseam (gentle C-curve) --
    inseam_mid = (crotch_pt + knee_inseam) / 2
    curve_inseam_upper = _bezier_quad(
        crotch_pt,
        inseam_mid + np.array([-0.3, 0.0]),  # slight inward bow toward creaseline
        knee_inseam,
    )

    # -- Sideseam upper: mid_side → knee_side (subtle shallow curve) --
    # P2 tangent matches the straight segment knee→hem_side_top for smooth flow.
    side_span_y = mid_side[1] - knee_side[1]
    side_hollow = 0.15  # cm inward (toward creaseline = rightward)
    leg_dir = knee_side - hem_side_top                    # direction of straight below
    leg_unit = leg_dir / np.linalg.norm(leg_dir)
    curve_side_upper = _bezier_cubic(
        mid_side,
        mid_side + np.array([side_hollow, -side_span_y / 3]),
        knee_side + leg_unit * (side_span_y / 3),         # arrives aligned with leg
        knee_side,
    )

    # -- Collect everything --
    points = {
        'A':                np.array([0.0, 0.0]),
        'hem_side':         hem_side,
        'hem_inseam':       hem_inseam,
        'hem_side_top':     hem_side_top,
        'hem_inseam_top':   hem_inseam_top,
        'hem_side_guide':   np.array([hem_side_guide_x, hem_y]),
        'hem_inseam_guide': np.array([hem_inseam_guide_x, hem_y]),
        'knee_side':        knee_side,
        'knee_inseam':      knee_inseam,
        'crotch_pt':        crotch_pt,
        'crotch_guide':     crotch_guide,
        'cf_at_crotch':     cf_at_crotch,   # construction only
        'cf_waist':         cf_waist,
        'cf_hip':           cf_hip,
        'mid_side':         mid_side,
        'hip_side':         hip_side,
        'waist_side':       np.array([waist_side_x, waist_y]),
        'waist_side_raised': waist_side_raised,
        'pleat':            pleat_pt,
    }

    levels = {
        'hemline':     hem_y,
        'knee line':   knee_y,
        'crotch line': crotch_y,
        'hipline':     hip_y,
        'waistline':   waist_y,
    }

    construction = {
        'ftw_x':             ftw_x,
        'fcw_mark_x':        fcw_mark_x,
        'crotch_pt_x':       crotch_pt_x,
        'creaseline_x':      creaseline_x,
        'cf_hip_x':          cf_hip_x,
        'cf_waist_x':        cf_waist_x,
        'mid_hip_crotch_y':  mid_hip_crotch_y,
        'hem_half':          hem_half,
        'pleat_x':           pleat_x,
    }

    curves = {
        'waistline':     curve_waistline,
        'hip':           curve_hip,
        'crotch':        curve_crotch,
        'inseam_upper':  curve_inseam_upper,
        'side_upper':    curve_side_upper,
    }

    return {
        'points': points,
        'levels': levels,
        'construction': construction,
        'curves': curves,
        'measurements': {
            'Wbg': Wbg, 'Hg': Hg, 'Hw': Hw, 'Sl': Sl, 'Is': Is,
            'Br': Br, 'Kh': Kh, 'Ftw': Ftw, 'Fcw': Fcw,
            'Cw': Cw, 'Bcw': Bcw, 'Btw': Btw,
            'cf_hip_x': cf_hip_x, 'cf_waist_x': cf_waist_x,
            'waist_side_x': waist_side_x,
        },
        'metadata': {'title': '1-Pleat Trouser Front (MM&S)'},
    }


# -- Visualization -----------------------------------------------------------

def plot_trouser_front(draft, output_path='Logs/trouser_front.svg',
                       debug=False, units='cm', step=5):
    """Render the trouser front draft up to the given step (1-5).

    step=1: framework only
    step=2: + widths and creaseline
    step=3: + hem widths, pleat, CF
    step=4: + shaping (knee, crotch guide, waist sideseam)
    step=5: + final curves and complete outline
    """
    pts = draft['points']
    lvl = draft['levels']
    con = draft['construction']
    mm  = draft['measurements']
    crv = draft['curves']

    fig, ax = plt.subplots(1, 1, figsize=(10, 16))
    plt.rcParams['lines.solid_capstyle'] = 'butt'
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
    CON = dict(color='cornflowerblue', linewidth=0.6, linestyle=':', alpha=0.5)
    x_max = con['fcw_mark_x'] + 5

    # ── Step 1: Framework ─────────────────────────────────────────
    # Horizontal reference lines
    for name, y in lvl.items():
        ax.plot([-2, x_max], [y, y], **REF)
        ax.annotate(name, (x_max, y), textcoords='offset points',
                    xytext=(4, 2), fontsize=7, color='gray')

    # Left vertical reference (A upward)
    ax.plot([0, 0], [-3, lvl['waistline'] + 5], 'k-', linewidth=0.8)

    # Dimension annotations (left side)
    for val, label, xoff in [(mm['Kh'], 'Kh', -5),
                              (mm['Is'], 'Is', -7),
                              (mm['Sl'], 'Sl', -9)]:
        ax.annotate('', xy=(-3, 0), xytext=(-3, val),
                    arrowprops=dict(arrowstyle='<->', color='dimgray', lw=0.7))
        ax.text(xoff, val / 2, f"{label}={val:.1f}", fontsize=6,
                color='dimgray', ha='right', va='center', rotation=90)

    # Point A
    ax.plot(0, 0, 'ko', markersize=5)
    ax.annotate('A', (0, 0), textcoords='offset points',
                xytext=(-8, -8), fontsize=9, fontweight='bold')

    if step < 2:
        _finish_plot(fig, ax, draft, output_path, step)
        return

    # ── Step 2: Widths and creaseline ─────────────────────────────
    # Ftw perpendicular (crotch → waist)
    ax.plot([con['ftw_x'], con['ftw_x']],
            [lvl['crotch line'], lvl['waistline']],
            'k-', linewidth=0.6, alpha=0.5)

    # Crotch point
    ax.plot(*pts['crotch_pt'], 'ko', markersize=4)
    ax.annotate('crotch pt', pts['crotch_pt'], textcoords='offset points',
                xytext=(4, -8), fontsize=6, color='black')

    # Creaseline (grainline)
    ax.plot([con['creaseline_x'], con['creaseline_x']],
            [-3, lvl['waistline'] + 3],
            'k-.', linewidth=0.6, alpha=0.5)
    ax.annotate('front creaseline', (con['creaseline_x'], -3),
                fontsize=7, color='black', ha='center', va='top')

    # Mid hip/crotch mark
    ax.plot([-1, 3], [con['mid_hip_crotch_y']] * 2, **CON)
    ax.annotate('1/2', (-1, con['mid_hip_crotch_y']), textcoords='offset points',
                xytext=(-8, 2), fontsize=6, color='cornflowerblue')

    # Ftw / Fcw dimension arrows
    ax.annotate('', xy=(0, lvl['hipline'] + 1),
                xytext=(con['ftw_x'], lvl['hipline'] + 1),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=0.6))
    ax.text(con['ftw_x'] / 2, lvl['hipline'] + 2.5, f"Ftw={mm['Ftw']:.1f}",
            fontsize=6, color='blue', ha='center')

    ax.annotate('', xy=(con['ftw_x'], lvl['hipline'] + 1),
                xytext=(con['fcw_mark_x'], lvl['hipline'] + 1),
                arrowprops=dict(arrowstyle='<->', color='blue', lw=0.6))
    ax.text((con['ftw_x'] + con['fcw_mark_x']) / 2, lvl['hipline'] + 2.5,
            f"Fcw={mm['Fcw']:.1f}", fontsize=6, color='blue', ha='center')

    if step < 3:
        _finish_plot(fig, ax, draft, output_path, step)
        return

    # ── Step 3: Hem widths, pleat, CF ─────────────────────────────
    # Hem width marks
    for pt_name in ('hem_side', 'hem_inseam'):
        p = pts[pt_name]
        ax.plot(p[0], p[1], 'k+', markersize=6)
    # Hem width dimension
    ax.annotate('', xy=(pts['hem_side'][0], -2),
                xytext=(con['creaseline_x'], -2),
                arrowprops=dict(arrowstyle='<->', color='green', lw=0.5))
    ax.text((pts['hem_side'][0] + con['creaseline_x']) / 2, -3.5,
            f"{con['hem_half']:.1f}", fontsize=6, color='green', ha='center')
    ax.annotate('', xy=(con['creaseline_x'], -2),
                xytext=(pts['hem_inseam'][0], -2),
                arrowprops=dict(arrowstyle='<->', color='green', lw=0.5))
    ax.text((con['creaseline_x'] + pts['hem_inseam'][0]) / 2, -3.5,
            f"{con['hem_half']:.1f}", fontsize=6, color='green', ha='center')

    # 0.5 cm guideline marks
    for pt_name in ('hem_side_guide', 'hem_inseam_guide'):
        p = pts[pt_name]
        ax.plot(p[0], p[1], 'x', color='gray', markersize=4)

    # Pleat symbol: spans from creaseline (right) to pleat_x (left)
    pr = con['creaseline_x']   # right edge (creaseline)
    pl = con['pleat_x']        # left edge (3.5 cm left)
    pm = (pr + pl) / 2         # midpoint
    py = lvl['waistline']
    chev_h = 1.5               # chevron height
    drop   = 6.0               # vertical lines extend below waist
    hw     = (pr - pl) / 2     # half-width
    # Vertical lines at pleat edges
    ax.plot([pl, pl], [py, py - drop], 'k-', linewidth=0.6, alpha=0.6)
    ax.plot([pr, pr], [py, py - drop], 'k-', linewidth=0.6, alpha=0.6)
    # Upper chevron (pointing down)
    ax.plot([pl, pm, pr], [py - 0.5, py - 0.5 - chev_h, py - 0.5],
            'k-', linewidth=0.8)
    # Lower chevron (pointing down)
    ax.plot([pl, pm, pr],
            [py - 0.5 - chev_h, py - 0.5 - 2 * chev_h, py - 0.5 - chev_h],
            'k-', linewidth=0.8)

    # CF line (angled: hipline → waistline)
    ax.plot([con['cf_hip_x'], con['cf_waist_x']],
            [lvl['hipline'], lvl['waistline']],
            'k-', linewidth=0.8, alpha=0.6)
    ax.annotate('CF', (con['cf_waist_x'], lvl['waistline']),
                textcoords='offset points', xytext=(4, 4),
                fontsize=7, fontweight='bold', color='black')

    # Sideseam guideline: hem_side_guide angled to mid_side (halfway between hip & crotch)
    ax.plot([pts['hem_side_guide'][0], pts['mid_side'][0]],
            [pts['hem_side_guide'][1], pts['mid_side'][1]],
            'k-', linewidth=0.5, alpha=0.4)

    # Inseam guideline: hem_inseam_guide angled to Fcw mark on hipline
    ax.plot([pts['hem_inseam_guide'][0], con['fcw_mark_x']],
            [pts['hem_inseam_guide'][1], lvl['hipline']],
            'k-', linewidth=0.5, alpha=0.4)

    if step < 4:
        _finish_plot(fig, ax, draft, output_path, step)
        return

    # ── Step 4: Shaping ───────────────────────────────────────────
    # Hem perpendiculars (~4 cm tall)
    for p in (pts['hem_side'], pts['hem_inseam']):
        ax.plot([p[0], p[0]], [p[1], p[1] + 4], **CON)

    # Knee points
    ax.plot(*pts['knee_side'], 'ko', markersize=3)
    ax.plot(*pts['knee_inseam'], 'ko', markersize=3)
    ax.annotate('knee (side)', pts['knee_side'], textcoords='offset points',
                xytext=(-10, -8), fontsize=5, color='gray')
    ax.annotate('knee (inseam)', pts['knee_inseam'], textcoords='offset points',
                xytext=(4, -8), fontsize=5, color='gray')

    # Crotch guide and slanted line
    ax.plot(*pts['crotch_guide'], 'o', color='cornflowerblue', markersize=4)
    ax.plot([pts['crotch_guide'][0], pts['crotch_pt'][0]],
            [pts['crotch_guide'][1], pts['crotch_pt'][1]], **CON)
    ax.annotate('crotch guide', pts['crotch_guide'], textcoords='offset points',
                xytext=(-12, 6), fontsize=5, color='cornflowerblue')

    # Waist sideseam point (only show un-raised version in step 4)
    if step < 5:
        ax.plot(*pts['waist_side'], 'ko', markersize=4)
        ax.annotate(f"waist side ({mm['waist_side_x']:.1f})",
                    pts['waist_side'], textcoords='offset points',
                    xytext=(-8, 6), fontsize=5, color='black')

    if step < 5:
        _finish_plot(fig, ax, draft, output_path, step)
        return

    # ── Step 5: Final curves and complete outline ─────────────────
    # Raised waist point
    ax.plot(*pts['waist_side_raised'], 'ko', markersize=4)

    # Waistline curve
    ax.plot(crv['waistline'][:, 0], crv['waistline'][:, 1],
            'k-', linewidth=1.5, zorder=4)

    # Sideseam upper straight: mid_side → hip_side
    ax.plot([pts['mid_side'][0], pts['hip_side'][0]],
            [pts['mid_side'][1], pts['hip_side'][1]],
            'k-', linewidth=1.5, zorder=4)

    # Hip curve (hip_side → raised waist, with intake)
    ax.plot(crv['hip'][:, 0], crv['hip'][:, 1],
            'k-', linewidth=1.5, zorder=4)

    # CF straight segment (waist → hipline)
    ax.plot([pts['cf_waist'][0], pts['cf_hip'][0]],
            [pts['cf_waist'][1], pts['cf_hip'][1]],
            'k-', linewidth=1.5, zorder=4)

    # Crotch curve (cf_top → crotch_pt)
    ax.plot(crv['crotch'][:, 0], crv['crotch'][:, 1],
            'k-', linewidth=1.5, zorder=4)

    # Inseam upper curve (crotch_pt → knee_inseam)
    ax.plot(crv['inseam_upper'][:, 0], crv['inseam_upper'][:, 1],
            'k-', linewidth=1.5, zorder=4)

    # Inseam lower: knee → hem_inseam_top (angled)
    ax.plot([pts['knee_inseam'][0], pts['hem_inseam_top'][0]],
            [pts['knee_inseam'][1], pts['hem_inseam_top'][1]],
            'k-', linewidth=1.5, zorder=4)

    # Hem perpendicular drops + hemline (one continuous polyline, butt caps)
    ax.plot([pts['hem_inseam_top'][0], pts['hem_inseam'][0],
             pts['hem_side'][0], pts['hem_side_top'][0]],
            [pts['hem_inseam_top'][1], pts['hem_inseam'][1],
             pts['hem_side'][1], pts['hem_side_top'][1]],
            'k-', linewidth=1.5, zorder=4, solid_capstyle='butt')

    # Sideseam: mid_side → knee (curve) → hem_side_top (angled)
    ax.plot(crv['side_upper'][:, 0], crv['side_upper'][:, 1],
            'k-', linewidth=1.5, zorder=4)
    ax.plot([pts['knee_side'][0], pts['hem_side_top'][0]],
            [pts['knee_side'][1], pts['hem_side_top'][1]],
            'k-', linewidth=1.5, zorder=4)

    # ── Debug: outline dimension annotations ──────────────────────
    if debug:
        _annotate_len(ax, crv['waistline'], offset=(0, 8))
        _annotate_len(ax, crv['hip'], offset=(-10, 0))
        _annotate_len(ax, crv['crotch'], offset=(6, 6))
        _annotate_len(ax, crv['inseam_upper'], offset=(8, 0))
        _annotate_len(ax, crv['side_upper'], offset=(-10, 0))
        _annotate_len(ax, np.array([pts['cf_waist'], pts['cf_hip']]), offset=(6, 0))
        _annotate_len(ax, np.array([pts['mid_side'], pts['hip_side']]), offset=(-10, 0))
        _annotate_len(ax, np.array([pts['knee_inseam'], pts['hem_inseam_top']]), offset=(8, 0))
        _annotate_len(ax, np.array([pts['knee_side'], pts['hem_side_top']]), offset=(-10, 0))
        _annotate_len(ax, np.array([pts['hem_side'], pts['hem_inseam']]), offset=(0, -8))

    _finish_plot(fig, ax, draft, output_path, step)


def _finish_plot(fig, ax, draft, output_path, step):
    """Common plot finalization."""
    title = f"{draft['metadata']['title']} — Step {step}"
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
    """Uniform interface called by the generic runner.

    Renders all 5 steps as separate SVGs plus the final combined output.
    """
    m = load_measurements(measurements_path)
    draft = draft_trouser_front(m)

    out = Path(output_path)
    stem = out.stem
    suffix = out.suffix or '.svg'
    parent = out.parent

    # Per-step SVGs
    for s in range(1, 6):
        step_path = parent / f"{stem}_step{s}{suffix}"
        plot_trouser_front(draft, str(step_path), debug=debug, units=units, step=s)

    # Final output at the requested path
    plot_trouser_front(draft, output_path, debug=debug, units=units, step=5)
