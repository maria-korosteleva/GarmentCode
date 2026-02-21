"""
verify_draft: double-check the 1873 jeans draft against body measurements.

Implements the checks from the "Double Checking Your Work" lesson:
  1. Waist         — (front waist + back waist − 3/4") × 2 ≈ waist
  2. Hips          — (front hip + back hip) × 2 ≈ seat + ~2" ease
  3. Fly & seat    — seam lengths minus 1½" waistband (for reference)
  4. Lengths       — side seam, front inseam; back curved inseam ≈ front − ¼"
  5. Widths        — hem and knee opening
"""

import numpy as np

from .jeans_front import INCH, load_measurements, draft_jeans_front, _curve_length
from .jeans_back import draft_jeans_back

WAISTBAND = 1.5 * INCH   # 1½" waistband deducted where the lesson specifies


def _seg(p0, p1):
    """Straight-line distance between two points."""
    return float(np.linalg.norm(np.asarray(p1) - np.asarray(p0)))


def _inch(cm):
    return cm / INCH


def _row(label, value_in, target_in=None, note="", tol_in=0.5):
    """Format one check row."""
    val_str = f'{value_in:.3f}"'
    if target_in is not None:
        diff = value_in - target_in
        ok = abs(diff) <= tol_in
        sym = "✓" if ok else "⚠"
        return f"  {label:<34} {val_str:>8}   target {target_in:.3f}\"  diff {diff:+.3f}\"  {sym}"
    else:
        return f"  {label:<34} {val_str:>8}   {note}"


def verify_draft(measurements_path):
    """
    Run all draft double-checks and print a report.

    Parameters
    ----------
    measurements_path : str or Path
        Path to the YAML measurements file.

    Returns
    -------
    str  — the formatted report (also printed to stdout).
    """
    m = load_measurements(measurements_path)
    front = draft_jeans_front(m)
    back  = draft_jeans_back(m, front)

    fpts   = front['points']
    fcurves = front['curves']
    bpts   = back['points']
    bcurves = back['curves']

    lines = []
    lines.append("=" * 65)
    lines.append("  DRAFT VERIFICATION  —  all values in inches")
    lines.append("=" * 65)

    # ── 1. WAIST ─────────────────────────────────────────────────────────
    #
    # Instruction: "measure the waist lines and subtract 3/4″; double that
    #              ≈ your waist measurement"
    #
    # "Waist lines" = front waist seam (rise curve 1'→7') +
    #                 back waist seam (straight 1→back_waist)  — one half.
    # Subtract 3/4" for the two SA joins at this half (CF corner 3/8" +
    # side-seam corner 3/8").  Double → full waist circle.
    #
    front_waist    = _curve_length(fcurves['rise'])
    back_waist     = _seg(fpts['1'], bpts['back_waist'])
    half_net       = front_waist + back_waist - 3/4 * INCH
    full_waist     = 2 * half_net
    waist_target   = m['waist']

    lines.append("\n── 1. WAIST ──")
    lines.append(_row("Front waist arc (1'→7')",     _inch(front_waist)))
    lines.append(_row("Back waist straight (1→bw)",  _inch(back_waist)))
    lines.append(_row("Half net (front+back − ¾\")",  _inch(half_net)))
    lines.append(_row("Full waist (×2)",              _inch(full_waist),
                       _inch(waist_target)))

    # ── 2. HIPS ──────────────────────────────────────────────────────────
    #
    # Instruction: "front: 4→8; back: 4 to seat seam perpendicular;
    #              compare to hip measurement — expect ~2" ease"
    #
    # Front hip: horizontal distance from pt4 (outseam at seat level)
    #            to pt8 (fly/crotch at seat level).
    # Back hip:  from pt4 to back 8', measured along the y-axis
    #            (perpendicular to the outseam, parallel to the seat line).
    # Both panels share the outseam at pt4, so we add the half-widths.
    #
    front_hip_half = abs(fpts['8'][1]      - fpts['4'][1])
    back_hip_half  = abs(bpts["8'"][1]  - fpts['4'][1])
    total_hip_half = front_hip_half + back_hip_half
    total_hip_full = 2 * total_hip_half
    seat_target    = m['seat']
    ease           = total_hip_full - seat_target

    lines.append("\n── 2. HIPS (at seat level) ──")
    lines.append(_row("Front hip half (4→8, horiz.)", _inch(front_hip_half)))
    lines.append(_row("Back hip half (4→8', horiz.)",    _inch(back_hip_half)))
    lines.append(_row("Total hip (×2)",                _inch(total_hip_full),
                       _inch(seat_target), tol_in=5.0))
    ease_ok = 1.0 * INCH <= ease <= 5.0 * INCH
    lines.append(f"  {'Ease':<34} {_inch(ease):>8.3f}\"   "
                 f"{'✓ (~2\" expected)' if ease_ok else '⚠ outside 1–5\" range'}")

    # ── 3. FLY & SEAT SEAMS ──────────────────────────────────────────────
    #
    # Instruction: "subtract 1½" for waistband; compare to your own
    #              measurements — may be off, use at first fitting"
    #
    # Fly seam  = rise curve (1'→7') + fly extension (7'→8), − 1½" wb.
    # Seat seam = seat_upper (back_waist→8', straight) +
    #             seat_lower (8'→11, curve), − 1½" wb.
    #
    fly_rise      = _curve_length(fcurves['rise'])
    fly_ext       = _seg(fpts["7'"], fpts['8'])
    fly_total_net = fly_rise + fly_ext - WAISTBAND

    seat_upper_len = _seg(bpts['back_waist'], bpts["8'"])
    seat_lower_len = _curve_length(bcurves['seat_lower'])
    seat_total_net = seat_upper_len + seat_lower_len - WAISTBAND

    lines.append("\n── 3. FLY & SEAT SEAMS (minus 1½\" waistband) ──")
    lines.append(_row("Rise arc (1'→7')",              _inch(fly_rise)))
    lines.append(_row("Fly extension (7'→8)",          _inch(fly_ext)))
    lines.append(_row("Fly seam total",                _inch(fly_total_net),
                       note="(no direct target — verify at fitting)"))
    lines.append(_row("Seat upper (back_waist→8')",    _inch(seat_upper_len)))
    lines.append(_row("Seat lower arc (8'→11)",        _inch(seat_lower_len)))
    lines.append(_row("Seat seam total",               _inch(seat_total_net),
                       note="(no direct target — verify at fitting)"))

    # ── 4. LENGTHS ───────────────────────────────────────────────────────
    #
    # Side seam (1'→4 arc + 4→0 straight).
    #   Our 'side_length' = body waist-to-hem.  The lesson says "minus 1½""
    #   because some drafts extend to include the waistband; ours does not,
    #   so we compare directly to side_length.
    #
    # Front inseam (6→3' arc + 3'→0' straight).
    #   Our 'inseam' = body crotch-to-hem, no waistband deduction needed.
    #
    # Back curved inseam (11→12) should be ≈ front curved (6→3') − ¼".
    #
    side_arc   = _curve_length(fcurves['hip'])
    side_str   = _seg(fpts['4'], fpts['0'])
    side_total = side_arc + side_str
    side_target = m['side_length']

    front_inseam_arc = _curve_length(fcurves['inseam'])
    front_inseam_str = _seg(fpts["3'"], fpts["0'"])
    front_inseam     = front_inseam_arc + front_inseam_str
    inseam_target    = m['inseam']

    back_inseam_arc  = _curve_length(bcurves['back_inseam'])
    back_front_diff  = back_inseam_arc - front_inseam_arc   # should be −¼"

    lines.append("\n── 4. LENGTHS ──")
    lines.append(_row("Side arc (1'→4)",               _inch(side_arc)))
    lines.append(_row("Side straight (4→0)",           _inch(side_str)))
    lines.append(_row("Side total",                    _inch(side_total),
                       _inch(side_target)))
    lines.append("")
    lines.append(_row("Front inseam arc (6→3')",       _inch(front_inseam_arc)))
    lines.append(_row("Front inseam straight (3'→0')", _inch(front_inseam_str)))
    lines.append(_row("Front inseam total",            _inch(front_inseam),
                       _inch(inseam_target)))
    lines.append("")
    lines.append(_row("Back curved inseam (11→12)",    _inch(back_inseam_arc)))
    lines.append(_row("Front curved inseam (6→3')",    _inch(front_inseam_arc)))
    back_ok = abs(back_front_diff + 0.25 * INCH) < 0.05 * INCH
    lines.append(f"  {'Back − front curved diff':<34} {_inch(back_front_diff):>+8.3f}\"   "
                 f"want −0.250\"  {'✓' if back_ok else '⚠'}")

    # ── 5. WIDTHS ────────────────────────────────────────────────────────
    #
    # Hem: front half = dist(0, 0'),  back extends 3/4" further → back half.
    #      Full opening = front_half + back_half.  By construction = hem_width.
    #
    # Knee: same logic — front half = dist(3, 3'),  back = front + 3/4" ext.
    #       Full opening = 2 × front_half + 3/4".   Should ≈ knee_width.
    #
    front_hem_half  = _seg(fpts['0'],  fpts["0'"])
    back_hem_half   = _seg(fpts['0'],  bpts['back_hem'])
    full_hem        = front_hem_half + back_hem_half
    hem_target      = m['hem_width']

    front_knee_half = abs(fpts["3'"][1] - fpts['3'][1])
    back_knee_ext   = 3/4 * INCH                          # same 3/4" ext as hem
    full_knee       = front_knee_half + (front_knee_half + back_knee_ext)
    knee_target     = m['knee_width']

    lines.append("\n── 5. WIDTHS ──")
    lines.append(_row("Front hem half (0→0')",         _inch(front_hem_half)))
    lines.append(_row("Back hem half (0→back_hem)",    _inch(back_hem_half)))
    lines.append(_row("Full hem opening",              _inch(full_hem),
                       _inch(hem_target)))
    lines.append("")
    lines.append(_row("Front knee half (3→3')",        _inch(front_knee_half)))
    lines.append(_row("Full knee opening",             _inch(full_knee),
                       _inch(knee_target)))

    lines.append("\n" + "=" * 65)

    report = "\n".join(str(l) for l in lines)
    print(report)
    return report


# -- Entry point for the generic runner -------------------------------------

def run(measurements_path, output_path=None, debug=False, units='inch'):
    """Uniform interface: runs verification and writes report to output_path.

    The runner may pass a .svg path; we replace the extension with .txt.
    """
    report = verify_draft(measurements_path)
    if output_path:
        from pathlib import Path
        txt_path = Path(output_path).with_suffix('.txt')
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(report)
        print(f"Report written to {txt_path}")
