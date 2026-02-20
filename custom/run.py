"""Generic TUI runner — select measurements and garment program via fzf."""
import argparse
import importlib
import subprocess
import sys
from datetime import date
from pathlib import Path

MEASUREMENTS_DIR = Path('custom/measurements')
PROGRAMS_DIR = Path('custom/garment_programs')


def _fzf_select(choices, prompt):
    """Pipe choices to fzf and return the selected one, or None."""
    if not choices:
        print(f"No options found for: {prompt}", file=sys.stderr)
        sys.exit(1)
    if len(choices) == 1:
        print(f"Auto-selected {choices[0]} (only option)")
        return choices[0]
    try:
        result = subprocess.run(
            ['fzf', '--prompt', f'{prompt}: '],
            input='\n'.join(choices),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("fzf not found. Install it or use --measurements and --program flags.", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        sys.exit(130)  # user cancelled
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurements', '-m', help='path to measurements YAML file')
    parser.add_argument('--program', '-p', help='garment program module name (e.g. jeans_front)')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='show construction lines, point labels, and grid')
    parser.add_argument('--units', '-u', choices=['cm', 'inch'], default=None,
                        help='display units for the plot (default: prompt via fzf)')
    args = parser.parse_args()

    # --- measurements selection ---
    if args.measurements:
        measurements_path = args.measurements
    else:
        yamls = sorted(str(p) for p in MEASUREMENTS_DIR.glob('*.yaml'))
        measurements_path = _fzf_select(yamls, 'Measurements')

    # --- program selection ---
    if args.program:
        program_name = args.program
    else:
        programs = sorted(
            p.stem for p in PROGRAMS_DIR.glob('*.py')
            if p.name != '__init__.py'
        )
        program_name = _fzf_select(programs, 'Program')

    # --- mode selection ---
    if args.debug:
        debug = True
    else:
        mode = _fzf_select(['pattern', 'debug (construction lines, labels, grid)'], 'Mode')
        debug = mode.startswith('debug')

    # --- units selection ---
    if args.units:
        units = args.units
    else:
        units = _fzf_select(['cm', 'inch'], 'Units')

    # --- import and run ---
    module = importlib.import_module(f'custom.garment_programs.{program_name}')
    output_path = f'Logs/{program_name}_{date.today()}.png'
    module.run(measurements_path, output_path, debug=debug, units=units)


if __name__ == '__main__':
    main()
