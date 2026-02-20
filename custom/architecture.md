# custom/ — Historical Tailoring Garment Programs

Personal garment drafting programs based on historical tailoring methods, built on top of the GarmentCode / pygarment infrastructure.

## Why a separate directory?

The main `assets/` tree uses anthropometric body models and pygarment's Panel/Component system. Our programs follow a different approach: **historical drafting methods** that work from a small set of tape measurements and procedural geometric constructions (points, lines, curves). Keeping them in `custom/` avoids mixing the two paradigms.

## Directory layout

```
custom/
├── architecture.md                          # This file
├── measurements/
│   └── justin.yaml                          # Personal body measurements (inches)
├── garment_programs/
│   ├── __init__.py
│   ├── jeans_front.py                       # Jeans front panel module
│   └── jeans_front_instructions.md          # Step-by-step drafting instructions
└── run.py                                   # Generic TUI runner (fzf-based)
```

## How to run

From the repo root, with the `.venv` activated:

```bash
# Interactive — uses fzf to pick measurements and program
python -m custom.run

# Non-interactive
python -m custom.run --measurements custom/measurements/justin.yaml --program jeans_front
```

Output goes to `Logs/{program_name}_{date}.png` (e.g. `Logs/jeans_front_2026-02-20.png`).

### Adding a new garment program

1. Create `custom/garment_programs/my_program.py`
2. Expose a `run(measurements_path, output_path)` function
3. It will automatically appear in the fzf selection

## Measurements

Measurements are stored in YAML in **inches** (how they're actually taken with a tape measure). The `load_measurements()` function converts to cm at load time, since all internal geometry is in cm.

To use different measurements, either edit `justin.yaml` or create a new file in `custom/measurements/`.

## Module structure

Each garment program module exposes:

- **`load_measurements(yaml_path)`** — reads YAML, converts units, returns a dict
- **`draft_*(m)`** — takes measurements dict, computes all points/curves/construction geometry, returns a structured result dict
- **`plot_*(draft, output_path)`** — renders the draft to a matplotlib figure
- **`run(measurements_path, output_path)`** — top-level entry point that calls load → draft → plot

This is intentionally procedural (not class-based). Historical drafting is a sequence of geometric operations, and functions map naturally to that.

## Design decisions

- **Bezier curves** for hip, rise, crotch, and inseam — cubic for curves needing tangent control at both ends, quadratic when passing through a specific midpoint
- **matplotlib for visualization** — not yet converted to pygarment Panel edges; that's a future step
- **All geometry in cm internally** — consistent with pygarment's coordinate system
- **Drafting instructions colocated** with the program code — `jeans_front_instructions.md` lives next to `jeans_front.py` so the source material is always at hand
- **Generic runner with fzf** — auto-discovers measurements and programs so adding a new garment only requires creating the module file
