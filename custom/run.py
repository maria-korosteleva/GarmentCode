"""Generic TUI runner — select measurements and garment program via fzf."""
import argparse
import importlib
import subprocess
import sys
from datetime import datetime
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


def _discover_garments():
    """Find packages that define a GARMENT dict in __init__.py."""
    garments = []
    for init in sorted(PROGRAMS_DIR.glob('*/__init__.py')):
        pkg = init.parent.name
        mod = importlib.import_module(f'custom.garment_programs.{pkg}')
        if hasattr(mod, 'GARMENT'):
            garments.append((pkg, mod.GARMENT))
    return garments


def _run_piece(pkg, piece_module, measurements_path, debug, units, output_dir=None):
    """Import and run a single piece module, returning the output path."""
    full_module = f'custom.garment_programs.{pkg}.{piece_module}'
    module = importlib.import_module(full_module)
    if output_dir:
        output_path = f'{output_dir}/{piece_module}.png'
    else:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output_path = f'Logs/{pkg}.{piece_module}_{timestamp}.png'
    module.run(measurements_path, output_path, debug=debug, units=units)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurements', '-m', help='path to measurements YAML file')
    parser.add_argument('--program', '-p', help='garment program module name (e.g. SelvedgeJeans1873 or SelvedgeJeans1873.jeans_front)')
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

    # --- discover garments ---
    garments = _discover_garments()
    garment_map = {pkg: garment for pkg, garment in garments}

    # --- program selection ---
    if args.program:
        program_name = args.program
    else:
        # Build choice list: garments first (with indented pieces), then standalone programs
        choices = []
        garment_pkgs = set()
        for pkg, garment in garments:
            choices.append(garment['name'])
            garment_pkgs.add(pkg)
            for piece in garment['pieces']:
                choices.append(f"  {piece['name']}")

        # Add standalone programs (not part of a garment package)
        standalone = sorted(
            str(p.relative_to(PROGRAMS_DIR)).replace('/', '.').removesuffix('.py')
            for p in PROGRAMS_DIR.rglob('*.py')
            if p.name != '__init__.py'
        )
        for prog in standalone:
            pkg_prefix = prog.split('.')[0] if '.' in prog else None
            if pkg_prefix not in garment_pkgs:
                choices.append(prog)

        selected = _fzf_select(choices, 'Program')

        # Resolve selection back to a program_name
        for pkg, garment in garments:
            if selected == garment['name']:
                program_name = pkg
                break
            for piece in garment['pieces']:
                if selected.strip() == piece['name']:
                    program_name = f"{pkg}.{piece['module']}"
                    break
            else:
                continue
            break
        else:
            # Standalone program selected as-is
            program_name = selected

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
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')

    if program_name in garment_map:
        # Run all pieces into a garment folder
        garment = garment_map[program_name]
        output_dir = f'Logs/{garment["name"]}_{timestamp}'
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        print(f"\n--- {garment['name']} ---")
        print(f"Output: {output_dir}/")
        outputs = []
        for piece in garment['pieces']:
            print(f"  Drafting {piece['name']}...")
            out = _run_piece(program_name, piece['module'], measurements_path, debug, units, output_dir=output_dir)
            outputs.append((piece['name'], out))
        print(f"\nGenerated {len(outputs)} pieces:")
        for name, path in outputs:
            print(f"  {name} -> {path}")
    else:
        # Single piece — may be dotted (pkg.module) or standalone
        parts = program_name.split('.', 1)
        if len(parts) == 2 and parts[0] in garment_map:
            _run_piece(parts[0], parts[1], measurements_path, debug, units)
        else:
            module = importlib.import_module(f'custom.garment_programs.{program_name}')
            output_path = f'Logs/{program_name}_{timestamp}.png'
            module.run(measurements_path, output_path, debug=debug, units=units)


if __name__ == '__main__':
    main()
