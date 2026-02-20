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
    pt1 = np.array([-(m['side_length'] - m['waistband_width']), 0.0])
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
    # 1. Side hip curve (1* -> 4)
    hip_curve_end = pt4.copy()
    dist_14 = np.linalg.norm(hip_curve_end - pt1_adj)
    rise_1 = hip_curve_end[1] - pt1_adj[1]
    curve_hip = _bezier_cubic(
        pt1_adj,
        pt1_adj + np.array([dist_14 / 3, rise_1]),
        hip_curve_end - np.array([dist_14 / 3, 0]),
        hip_curve_end
    )

    # 2. Front rise curve (1* -> 7*)
    dist_17 = np.linalg.norm(pt7_adj - pt1_adj)
    curve_rise = _bezier_cubic(
        pt1_adj,
        pt1_adj + np.array([0, -dist_17 / 3]),
        pt7_adj + np.array([0, dist_17 / 3]),
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
            '1*': pt1_adj, '7*': pt7_adj, '9': pt9,
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

def plot_jeans_front(draft, output_path='Logs/jeans_front.png'):
    """Render the draft to a matplotlib figure and save as PNG."""
    pts = draft['points']
    curves = draft['curves']
    con = draft['construction']

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))

    # Baseline
    baseline_pts_sorted = sorted(
        [pts['0'], pts['1'], pts['2'], pts['3'], pts['4']],
        key=lambda p: p[0],
    )
    ax.plot(
        [baseline_pts_sorted[0][0] - 5, baseline_pts_sorted[-1][0] + 5],
        [0, 0], 'k-', linewidth=0.5, alpha=0.2,
    )

    # Drop lines
    for base_k, drop_k in [('0', "0'"), ('3', "3'"), ('2', '5'), ('4', '8'), ('1', '7')]:
        ax.plot(
            [pts[base_k][0], pts[drop_k][0]],
            [pts[base_k][1], pts[drop_k][1]],
            'k--', linewidth=0.5, alpha=0.1,
        )
    ax.plot([pts['5'][0], pts['6'][0]], [pts['5'][1], pts['6'][1]],
            'k--', linewidth=0.5, alpha=0.1)

    # Construction: fly line
    ax.plot([con['fly_start'][0], con['fly_end'][0]],
            [con['fly_start'][1], con['fly_end'][1]],
            'k--', linewidth=0.5, alpha=0.15)
    # Construction: inseam straight
    ax.plot([pts['6'][0], pts["3'"][0], pts["0'"][0]],
            [pts['6'][1], pts["3'"][1], pts["0'"][1]],
            'k--', linewidth=0.5, alpha=0.15)

    # Curves
    c = curves
    ax.plot(c['hip'][:, 0], c['hip'][:, 1],
            'b-', linewidth=2, label='1. Side hip (1*->4)', zorder=4)
    ax.plot(c['rise'][:, 0], c['rise'][:, 1],
            'r-', linewidth=2, label='2. Front rise (1*->7*)', zorder=4)
    ax.plot(c['crotch'][:, 0], c['crotch'][:, 1],
            'g-', linewidth=2, label='3. Crotch (8->9->6)', zorder=4)
    ax.plot(c['inseam'][:, 0], c['inseam'][:, 1],
            'm-', linewidth=2, label="4. Inseam (6->3')", zorder=4)

    # Straight segments
    ax.plot([pts['4'][0], pts['0'][0]], [pts['4'][1], pts['0'][1]],
            'k-', linewidth=1.5, alpha=0.5, label='Straight segments')
    ax.plot([pts['7*'][0], pts['8'][0]], [pts['7*'][1], pts['8'][1]],
            'k-', linewidth=1.5, alpha=0.5)
    ax.plot([pts["3'"][0], pts["0'"][0]], [pts["3'"][1], pts["0'"][1]],
            'k-', linewidth=1.5, alpha=0.5)
    ax.plot([pts["0'"][0], pts['0'][0]], [pts["0'"][1], pts['0'][1]],
            'k-', linewidth=1.5, alpha=0.5)

    # Center front line (Step 6)
    ax.plot([pts['2'][0], pts['5'][0]], [pts['2'][1], pts['5'][1]],
            'c--', linewidth=0.5, alpha=0.2)
    ax.plot(pts['temp'][0], pts['temp'][1], 'x', color='cyan',
            markersize=5, alpha=0.4, zorder=5)
    ax.plot([pts['1'][0] - 5, pts['0'][0] + 5],
            [pts['10'][1], pts['10'][1]],
            'c-', linewidth=1.2, alpha=0.5, label='6. CF line')
    ax.plot(pts['10'][0], pts['10'][1], 's', color='cyan',
            markersize=7, zorder=6, label='Point 10 (CF)')

    # All key points
    for name, pt in pts.items():
        if name == 'temp':
            continue
        ax.plot(pt[0], pt[1], 'o', color='gray', markersize=4, zorder=5, alpha=0.5)
        ax.annotate(name, pt, textcoords="offset points",
                    xytext=(6, 4), ha='left', fontsize=8, alpha=0.6)

    ax.legend(loc='lower right', fontsize=9)
    ax.set_xlabel('cm')
    ax.set_ylabel('cm')
    ax.set_title(draft['metadata']['title'])
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.2)
    ax.margins(0.05)

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved visualization to {output_path}")


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path):
    """Uniform interface called by the generic runner."""
    m = load_measurements(measurements_path)
    draft = draft_jeans_front(m)
    plot_jeans_front(draft, output_path)
