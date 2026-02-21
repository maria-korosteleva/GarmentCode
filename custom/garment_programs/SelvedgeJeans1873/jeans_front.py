"""
Historical Jeans Front Panel (1873 style)
Based on: Historical Tailoring Masterclasses - Drafting the Front

Refactored from the step-by-step exploration into a reusable module.
"""
import yaml
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

INCH = 2.54  # cm per inch


def load_measurements(yaml_path):
    """Load measurements from YAML, converting inches to cm."""
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


# -- Arc-length walk helpers ------------------------------------------------

def _point_at_arclength(curve, dist):
    """Interpolated (x, y) at *dist* arc-length from the start of a polyline."""
    diffs = np.diff(curve, axis=0)
    seg_lengths = np.sqrt(diffs[:, 0]**2 + diffs[:, 1]**2)
    cum = np.concatenate([[0.0], np.cumsum(seg_lengths)])
    if dist <= 0:
        return curve[0].copy()
    if dist >= cum[-1]:
        return curve[-1].copy()
    idx = max(0, int(np.searchsorted(cum, dist)) - 1)
    idx = min(idx, len(curve) - 2)
    t = (dist - cum[idx]) / seg_lengths[idx]
    return curve[idx] * (1 - t) + curve[idx + 1] * t


def _curve_up_to_arclength(curve, dist):
    """Sub-polyline from ``curve[0]`` to the point at *dist* arc-length."""
    diffs = np.diff(curve, axis=0)
    seg_lengths = np.sqrt(diffs[:, 0]**2 + diffs[:, 1]**2)
    cum = np.concatenate([[0.0], np.cumsum(seg_lengths)])
    if dist >= cum[-1]:
        return curve.copy()
    idx = max(0, int(np.searchsorted(cum, dist)) - 1)
    idx = min(idx, len(curve) - 2)
    t = (dist - cum[idx]) / seg_lengths[idx]
    endpoint = curve[idx] * (1 - t) + curve[idx + 1] * t
    return np.vstack([curve[:idx + 1], endpoint.reshape(1, 2)])


# -- Measurement annotation helpers -----------------------------------------

def _curve_length(pts):
    """Arc length of a polyline (Nx2 array)."""
    diffs = np.diff(pts, axis=0)
    return np.sum(np.sqrt(diffs[:, 0]**2 + diffs[:, 1]**2))


def _annotate_curve(ax, pts, offset=(0, 6)):
    """Label a curve with its arc length at the midpoint."""
    length = _curve_length(pts)
    mid = pts[len(pts) // 2]
    ax.annotate(f'{length:.1f}', mid, textcoords="offset points",
                xytext=offset, fontsize=6, color='darkblue', ha='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))


def _annotate_segment(ax, p0, p1, offset=(0, 6)):
    """Label a straight segment with its length at the midpoint."""
    length = np.linalg.norm(p1 - p0)
    mid = (p0 + p1) / 2
    ax.annotate(f'{length:.1f}', mid, textcoords="offset points",
                xytext=offset, fontsize=6, color='darkblue', ha='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))


# -- Seam-allowance offset helper -------------------------------------------

def _offset_polyline(pts, distance):
    """Offset a polyline by *distance* to the left of the travel direction.

    For a clockwise outline, positive *distance* pushes outward.

    Parameters
    ----------
    pts : ndarray, shape (N, 2)
        Ordered polyline vertices.
    distance : float
        Offset distance (positive = left of travel = outward for CW).

    Returns
    -------
    ndarray, shape (N, 2)
        Offset polyline (same number of points, miter-joined).
    """
    pts = np.asarray(pts, dtype=float)
    n = len(pts)
    if n < 2:
        return pts.copy()

    # Per-segment unit normals (left of travel direction)
    seg = np.diff(pts, axis=0)                       # (N-1, 2)
    lengths = np.sqrt(seg[:, 0]**2 + seg[:, 1]**2)
    lengths = np.where(lengths == 0, 1e-12, lengths)  # avoid div-by-zero
    normals = np.column_stack([-seg[:, 1], seg[:, 0]]) / lengths[:, None]

    out = np.empty_like(pts)

    # First and last points: simple normal offset
    out[0] = pts[0] + normals[0] * distance
    out[-1] = pts[-1] + normals[-1] * distance

    # Interior points: average of adjacent normals (miter)
    for i in range(1, n - 1):
        avg = normals[i - 1] + normals[i]
        length = np.linalg.norm(avg)
        if length < 1e-12:
            avg = normals[i]
        else:
            avg = avg / length
        # Miter scale: project onto either normal
        cos_half = np.dot(avg, normals[i])
        if abs(cos_half) < 0.1:
            cos_half = 0.1  # cap for very sharp corners
        out[i] = pts[i] + avg * (distance / cos_half)

    return out


def _draw_seam_allowance(ax, edges, scale=1.0):
    """Draw a continuous seam-allowance boundary for an ordered list of edges.

    Edges must be ordered so that they form a continuous CW perimeter
    (each edge's last point ≈ the next edge's first point).  The function
    offsets each edge by its SA, then connects adjacent offset segments at
    their intersection (miter point) to produce one unbroken cutting line.

    Parameters
    ----------
    ax : matplotlib Axes
    edges : list of (pts, sa_distance) tuples
        *pts* is an (N,2) ndarray (already display-scaled),
        *sa_distance* is the seam allowance in **cm** (pre-scaling).
    scale : float
        Display scale factor (e.g. 1/INCH for inch mode).
    """
    SA_STYLE = dict(color='gray', linewidth=0.6, linestyle='--', alpha=0.5)

    # Offset each edge independently
    offsets = []
    for pts, sa_cm in edges:
        sa = sa_cm * scale
        offsets.append(_offset_polyline(pts, sa))

    # Build continuous SA path by connecting offset segments at corners
    sa_pts = list(offsets[0])
    for i in range(1, len(offsets)):
        # Connect: add the first point of the next segment
        # (creates a short connecting line at the SA transition)
        sa_pts.extend(offsets[i].tolist())

    # Close the loop back to the starting point
    sa_pts.append(sa_pts[0])
    sa_path = np.array(sa_pts)
    ax.plot(sa_path[:, 0], sa_path[:, 1], **SA_STYLE)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_front(m):
    """
    Compute all points, curves, and construction geometry for the jeans front.

    Parameters
    ----------
    m : dict
        Measurements in cm (output of load_measurements).

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    # Step 1: Marking out the lengths
    pt0 = np.array([0.0, 0.0])
    pt1 = np.array([-m['side_length'], 0.0])
    pt2 = np.array([-m['inseam'], 0.0])
    pt3 = np.array([pt2[0] / 2 - 2 * INCH, 0.0])
    pt4 = np.array([pt2[0] - (m['seat'] / 2) / 6, 0.0])

    # Step 2: Marking out the widths
    hem_drop = m['hem_width'] / 2 - 3/8 * INCH
    pt0_drop = np.array([pt0[0], -hem_drop])

    knee_drop = m['knee_width'] / 2 - 3/8 * INCH
    pt3_drop = np.array([pt3[0], -knee_drop])

    seat_quarter = m['seat'] / 4
    pt5 = np.array([pt2[0], -seat_quarter])

    crotch_ext = (m['seat'] / 2) / 6 - 1 * INCH
    pt6 = np.array([pt5[0], pt5[1] - crotch_ext])

    pt7 = np.array([pt1[0], -seat_quarter])
    pt8 = np.array([pt4[0], -seat_quarter])

    # Step 3: Point adjustments
    pt1_adj = pt1.copy()
    pt1_adj[1] -= 3/8 * INCH

    dir_7to8 = pt8 - pt7
    dir_7to8_norm = dir_7to8 / np.linalg.norm(dir_7to8)
    pt7_shifted = pt7 + dir_7to8_norm * (3/8 * INCH)
    pt7_adj = pt7_shifted.copy()
    pt7_adj[1] += 5/8 * INCH

    dist_5to6 = np.linalg.norm(pt6 - pt5)
    half_dist = dist_5to6 / 2
    pt9 = pt5 + half_dist * np.array([-np.cos(np.pi/4), -np.sin(np.pi/4)])

    # Step 4: Construction lines
    fly_dir = pt8 - pt7_adj
    fly_dir_norm = fly_dir / np.linalg.norm(fly_dir)
    fly_start = pt7_adj
    fly_end = pt8 + fly_dir_norm * 5

    # Step 5: Curves
    # 1. Side hip curve (1' -> 4)
    hip_curve_end = pt4.copy()
    dist_14 = np.linalg.norm(hip_curve_end - pt1_adj)
    rise_1 = hip_curve_end[1] - pt1_adj[1]
    curve_hip = _bezier_cubic(
        pt1_adj,
        pt1_adj + np.array([dist_14 / 3, rise_1]),
        hip_curve_end - np.array([dist_14 / 3, 0]),
        hip_curve_end
    )

    # 2. Front rise / waist curve (1' -> 7')
    # Both endpoints tangent in the −y direction (toward the side seam).
    # This guarantees a C-curve with no inflection: the x-component of the
    # Bézier is the product of two non-negative Bernstein terms → monotone.
    # The curve bows slightly toward the hem (+x) at the midpoint — the
    # natural "waist dip" shape — and arrives at pt7_adj flowing toward the
    # side seam, as required.
    y_arm = abs(pt7_adj[1] - pt1_adj[1]) / 3   # ≈ 1/3 of the y-span
    curve_rise = _bezier_cubic(
        pt1_adj,
        pt1_adj + np.array([0.0, -y_arm]),   # tangent: straight toward side seam
        pt7_adj + np.array([0.0,  y_arm]),   # tangent: arriving from the side seam
        pt7_adj
    )

    # 3. Crotch curve (8 -> 9 -> 6)
    crotch_ctrl = 2 * pt9 - 0.5 * (pt8 + pt6)
    curve_crotch = _bezier_quad(pt8, crotch_ctrl, pt6)

    # 4. Inseam curve (6 -> 3')
    dir_6_to_3 = pt3_drop - pt6
    dir_6_to_3_norm = dir_6_to_3 / np.linalg.norm(dir_6_to_3)
    angle = np.radians(20)
    inseam_tan_at_6 = np.array([
        dir_6_to_3_norm[0] * np.cos(angle) - dir_6_to_3_norm[1] * np.sin(angle),
        dir_6_to_3_norm[0] * np.sin(angle) + dir_6_to_3_norm[1] * np.cos(angle)
    ])
    inseam_straight_dir = pt0_drop - pt3_drop
    inseam_straight_dir_norm = inseam_straight_dir / np.linalg.norm(inseam_straight_dir)
    dist_63 = np.linalg.norm(pt3_drop - pt6)
    curve_inseam = _bezier_cubic(
        pt6,
        pt6 + inseam_tan_at_6 * (dist_63 / 4),
        pt3_drop - inseam_straight_dir_norm * (dist_63 / 4),
        pt3_drop
    )

    # Step 6: Center front line
    dist_2to5 = np.linalg.norm(pt5 - pt2)
    half_2to5 = dist_2to5 / 2
    dir_2to5 = (pt5 - pt2) / dist_2to5
    pt_temp = pt2 + dir_2to5 * half_2to5
    pt10 = pt_temp - dir_2to5 * (3/4 * INCH)

    return {
        'points': {
            '0': pt0, '1': pt1, '2': pt2, '3': pt3, '4': pt4,
            "0'": pt0_drop, "3'": pt3_drop,
            '5': pt5, '6': pt6, '7': pt7, '8': pt8,
            "1'": pt1_adj, "7'": pt7_adj, '9': pt9,
            '10': pt10, 'temp': pt_temp,
        },
        'curves': {
            'hip': curve_hip,
            'rise': curve_rise,
            'crotch': curve_crotch,
            'inseam': curve_inseam,
        },
        'construction': {
            'fly_start': fly_start,
            'fly_end': fly_end,
        },
        'metadata': {
            'title': 'Historical Jeans Front Panel (1873)',
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_front(draft, output_path='Logs/jeans_front.svg', debug=False, units='cm'):
    """Render the draft to a matplotlib figure and save as PNG.

    Always draws the pattern outline and internal reference lines (hip, knee, CF).
    With debug=True, adds construction lines, point labels, legend, and grid.

    units : 'cm' or 'inch' — display unit for axes and annotations.
    """
    s = 1 / INCH if units == 'inch' else 1.0  # display scale factor
    unit_label = 'in' if units == 'inch' else 'cm'
    pts = {k: v * s for k, v in draft['points'].items()}
    curves = {k: v * s for k, v in draft['curves'].items()}
    con = {k: v * s for k, v in draft['construction'].items()}
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))

    # --- Debug-only: construction scaffolding ---
    if debug:
        # Baseline
        baseline_xs = sorted(p[0] for p in [pts['0'], pts['1'], pts['2'], pts['3'], pts['4']])
        ax.plot([baseline_xs[0] - 5, baseline_xs[-1] + 5], [0, 0],
                'k-', linewidth=0.5, alpha=0.2)

        # Drop lines
        for base_k, drop_k in [('0', "0'"), ('3', "3'"), ('2', '5'), ('4', '8'), ('1', '7')]:
            ax.plot([pts[base_k][0], pts[drop_k][0]],
                    [pts[base_k][1], pts[drop_k][1]],
                    'k--', linewidth=0.5, alpha=0.1)
        ax.plot([pts['5'][0], pts['6'][0]], [pts['5'][1], pts['6'][1]],
                'k--', linewidth=0.5, alpha=0.1)

        # Fly line
        ax.plot([con['fly_start'][0], con['fly_end'][0]],
                [con['fly_start'][1], con['fly_end'][1]],
                'k--', linewidth=0.5, alpha=0.15)
        # Inseam straight
        ax.plot([pts['6'][0], pts["3'"][0], pts["0'"][0]],
                [pts['6'][1], pts["3'"][1], pts["0'"][1]],
                'k--', linewidth=0.5, alpha=0.15)

        # CF construction (2→5 dashed)
        ax.plot([pts['2'][0], pts['5'][0]], [pts['2'][1], pts['5'][1]],
                'c--', linewidth=0.5, alpha=0.2)

    # --- Pattern outline: curves ---
    c = curves
    if debug:
        ax.plot(c['hip'][:, 0], c['hip'][:, 1],
                'b-', linewidth=2, label="Side hip (1'->4)", zorder=4)
        ax.plot(c['rise'][:, 0], c['rise'][:, 1],
                'r-', linewidth=2, label="Front rise (1'->7')", zorder=4)
        ax.plot(c['crotch'][:, 0], c['crotch'][:, 1],
                'g-', linewidth=2, label='Crotch (8->9->6)', zorder=4)
        ax.plot(c['inseam'][:, 0], c['inseam'][:, 1],
                'm-', linewidth=2, label="Inseam (6->3')", zorder=4)
    else:
        for curve in c.values():
            ax.plot(curve[:, 0], curve[:, 1], 'k-', linewidth=1.5)

    # --- Pattern outline: straight segments ---
    for a, b in [('4', '0'), ("7'", '8'), ("3'", "0'"), ("0'", '0')]:
        ax.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]],
                'k-', linewidth=1.5)

    # --- Internal reference lines (always shown) ---
    # y-range for vertical lines (span the full width of the pattern)
    y_lo = min(pts['6'][1], pts['5'][1]) - 2
    y_hi = 2

    # Seat line — vertical at pt4 x-level (just above crotch fork)
    seat_x = pts['4'][0]
    ax.plot([seat_x, seat_x], [y_lo, y_hi], **REF)
    ax.annotate('seat', (seat_x, y_hi), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    # Hip line — vertical at the crotch-fork x-level
    hip_x = pts['2'][0]
    ax.plot([hip_x, hip_x], [y_lo, y_hi], **REF)
    ax.annotate('hip', (hip_x, y_hi), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    # Knee line — vertical at knee x-level
    knee_x = pts['3'][0]
    ax.plot([knee_x, knee_x], [y_lo, y_hi], **REF)
    ax.annotate('knee', (knee_x, y_hi), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    # Center front line — horizontal at CF y-offset
    x_left, x_right = pts['1'][0] - 3, pts['0'][0] + 3
    cf_mid = (x_left + x_right) / 2
    ax.plot([x_left, x_right], [pts['10'][1], pts['10'][1]], **REF)
    ax.annotate('center front', (cf_mid, pts['10'][1]), textcoords="offset points",
                xytext=(0, 4), fontsize=7, color='gray', ha='center')

    # --- Debug-only: point labels, legend, grid ---
    if debug:
        for name, pt in pts.items():
            if name == 'temp':
                continue
            ax.plot(pt[0], pt[1], 'o', color='gray', markersize=4, zorder=5, alpha=0.5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=8, alpha=0.6)
        ax.legend(loc='lower right', fontsize=9)
        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)

        # Measurement annotations
        _annotate_curve(ax, curves['hip'], offset=(0, -10))
        _annotate_curve(ax, curves['rise'], offset=(-10, 0))
        _annotate_curve(ax, curves['crotch'], offset=(0, -10))
        _annotate_curve(ax, curves['inseam'], offset=(10, 0))
        _annotate_segment(ax, pts['4'], pts['0'], offset=(0, 8))
        _annotate_segment(ax, pts["7'"], pts['8'])
        _annotate_segment(ax, pts["3'"], pts["0'"], offset=(10, 0))
        _annotate_segment(ax, pts["0'"], pts['0'], offset=(8, 0))

    # --- Seam allowances (always drawn) ---
    # SA values in cm (from the Seam Allowances lesson)
    SA_SIDE   = 3/4 * INCH    # side seam
    SA_HEM    = (1.5 + 7/8) * INCH  # 2 3/8" (1 1/2" turn-up + 7/8" hem)
    SA_INSEAM = 3/8 * INCH    # inseam
    SA_CROTCH = 3/8 * INCH    # crotch / fly
    SA_FLY    = 3/4 * INCH    # fly extension (3/8" crotch + 3/8" additional)
    SA_WAIST  = 3/8 * INCH    # waist

    # SA transition: 3/4" kicks in 1/2" before pt8 on the crotch curve
    _crotch_rev = curves['crotch'][::-1]          # scaled, pt6 → pt8
    _crotch_len = _curve_length(_crotch_rev)
    _split      = 0.5 * INCH * s
    _crotch_body = _curve_up_to_arclength(_crotch_rev, _crotch_len - _split)
    _crotch_end  = _curve_up_to_arclength(_crotch_rev[::-1], _split)[::-1]

    # Build edges: (polyline, sa_distance_cm)
    # Outline travels CW: hip(1'→4) → hem(4→0) → hem_drop(0→0') → inseam(0'→3')
    #   → inseam_curve(3'→6) → crotch(6→8) → fly(8→7') → rise(7'→1')
    sa_edges = [
        (curves['hip'],                                          SA_SIDE),    # side seam (waist→seat)
        (np.array([pts['4'], pts['0']]),                         SA_SIDE),    # side seam (seat→hem)
        (np.array([pts['0'], pts["0'"]]),                        SA_HEM),     # hem
        (np.array([pts["0'"], pts["3'"]]),                       SA_INSEAM),  # lower inseam straight
        (curves['inseam'][::-1],                                 SA_INSEAM),  # inseam curve (3'→6)
        (_crotch_body,                                           SA_CROTCH),  # crotch (6 → transition)
        (_crotch_end,                                            SA_FLY),     # last 1/2" of crotch: 3/4"
        (np.array([pts['8'], pts["7'"]]),                        SA_FLY),     # fly: full 3/4"
        (curves['rise'][::-1],                                   SA_WAIST),   # rise / waist (7'→1')
    ]
    _draw_seam_allowance(ax, sa_edges, scale=s)

    ax.set_title(draft['metadata']['title'])
    ax.set_aspect('equal')
    ax.margins(0.05)
    if not debug:
        ax.axis('off')

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved visualization to {output_path}")


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm'):
    """Uniform interface called by the generic runner."""
    m = load_measurements(measurements_path)
    draft = draft_jeans_front(m)
    plot_jeans_front(draft, output_path, debug=debug, units=units)
