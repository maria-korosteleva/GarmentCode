# GarmentCode for Weon
This is the fork of GarmentCode for Weon.

## Installation

```
git clone https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode.git
git clone git@github.com:spacemoses-mafia/weon-garmentcode.git

cd weon-garmentcode
uv venv --python 3.11
source .venv/bin/activate
uv pip install pygarment

cd ../NvidiaWarp-GarmentCode
chmod +x ./tools/packman/packman
python build_lib.py --cuda_path="/usr/local/cuda"
uv pip install -e .

apt-get update
apt-get install libglfw3-dev libgles2-mesa-dev -y
```



## Documents

1. [Running Configurator](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Running_garmentcode.md) 
2. [Running Data Generation (warp)](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Running_data_generation.md) 
3. [Body measurements Description](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Body%20Measurements%20GarmentCode.pdf)
4. [Dataset documentation](https://www.research-collection.ethz.ch/handle/20.500.11850/673889)

## Pattern Dataset Generation & Simulation

The `pattern_data_sim.py` script provides a unified workflow for generating sewing patterns and running simulations.

### Basic Usage

**Generate and simulate from a design file:**
```bash
python pattern_data_sim.py --design <design_file.yaml> --name <dataset_name>
```

### Common Options

- `--design, -d`: Path to design parameters YAML file (required)
- `--name, -n`: Name of the dataset (default: `design_fit`)
- `--config, -c`: Simulation/rendering config file (JSON/YAML) (default: `default_sim_props.yaml`)
- `--skip_simulation`: Skip simulation, only generate dataset
- `--perfect-fit`: Use perfect fit garment specification format
- `--verbose, -v`: Print verbose output
- `--caching`: Cache intermediate simulation results
- `--rewrite_config`: Re-write simulation config even if it exists

### Examples

```bash
# Generate dataset and simulate
python pattern_data_sim.py --design assets/design_params/pants_M.yaml --name my_pants

# Generate dataset only (skip simulation)
python pattern_data_sim.py --design assets/design_params/shirt_L.yaml --name my_shirt --skip_simulation

# Use custom simulation config
python pattern_data_sim.py --design assets/design_params/pants_M.yaml --name my_pants --config my_sim_config.json

# Use perfect fit specification
python pattern_data_sim.py --design assets/design_params/perfect_fit_garment_spec.yaml --perfect-fit --name perfect_fit_pants
```

> **Note:** Ensure `system.json` is configured with appropriate paths before running. The script can be executed in Maya (or via `mayapy`) for simulation.

## Navigation

### Library

[PyGarment](https://github.com/maria-korosteleva/GarmentCode/tree/main/pygarment) is the core library described in the GarmentCode paper. It contains the base types (Edge, Panel, Component, Interface, etc.), as well as edge factory and various helpers and operators that help you design sewing patterns.  


### Examples

* [assets/garment_programs/](https://github.com/maria-korosteleva/GarmentCode/tree/main/assets/garment_programs/) contains the code of garment components designed using PyGarment. 
* [assets/design_params/](https://github.com/maria-korosteleva/GarmentCode/tree/main/assets/design_params/), [assets/bodies/](https://github.com/maria-korosteleva/GarmentCode/tree/main/assets/bodies/) contain examples of design and body measurements presets. They can be used in both GarmentCode GUI and `test_garmentcode.py` script.

> NOTE: [assets/design_params/default.yaml](https://github.com/maria-korosteleva/GarmentCode/blob/main/assets/design_params/default.yaml) is the setup used by GUI on load. Changing this file results in changes in the GUI initial state =) 
