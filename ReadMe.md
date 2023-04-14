
# GarmentCode: Programming Parametric Sewing Patterns

Implementation of GarmentCode architecture and garment programs.

## Installation

### Install python with dependencies:

* Python 3.9
* numpy
* scipy
* [svgwrite](https://pypi.org/project/svgwrite/)
* psutil
* matplotlib
* [svgpathtools](https://github.com/mathandy/svgpathtools)
* [cairoSVG](https://cairosvg.org/)
    NOTE: this lib has some quirks on Windows, which we relove with including needed dlls in `./patttern/cairo_dlls` and adding the ditrectory to PATH in runtime
* [PySimpleGUI](https://github.com/PySimpleGUI/PySimpleGUI) to run GUI script

All python dependencies can be installed with `pip install` / `conda install`

=> The code is ready to run

NOTE: 
* The dependency on [Pattern Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator)in included in the repo (`./external`), and will be loaded automatically by test script
* The environemtal variables needed for correct lib loading are set up in the test script

### Configuration of local paths

Same as here: https://github.com/maria-korosteleva/Garment-Pattern-Generator/blob/master/docs/Installation.md#local-paths-setup

NOTE: ATM only the 'output' path is actually used, so setting only that one is enough


## How to run (command line)

From the root directory run
```
python test_garments.py
```

It will create sewing pattern for the current state of `assets/design_params/base.yaml` for average SMPL body, and put it to the logs folder. Modify the parameters inside the script as needed.

## How to run (GUI)

WARNING: Currently in active development, quality not guaranteed 😅

From the root directory run
```
python gui.py
```

It can load body and design parameter files and display the corresponding sewing pattern right away.
Design files should be compatible with `MetaGarment` object (all examples provided in `assets\design_params` are compatible).

SOON: displaying garment parameters for direct manipulation

## Modifying the parameters

`./assets/design_params/base.yaml` contains the full set of style parameters for creating samples of our garment configurator.

* Update some of parameter values ('v:' field under parameter name) withing a given range 
* run `test_garments.py` 
* `./Logs/base_<timestamp>` will contain the sewing patterns corresponding to given values


## Attribution
We are using samples from [SMPL](https://smpl.is.tue.mpg.de/) body model as base for [Body Model examples](assets/Bodies). 
