
# GarmentCode: Programming Parametric Sewing Patterns

Implementation of GarmentCode architecture and garment programs.

## Installation

### Install python with dependencies:

* Python 3.9
* numpy
* scipy
* pyaml
* [svgwrite](https://pypi.org/project/svgwrite/)
* psutil
* matplotlib
* [svgpathtools](https://github.com/mathandy/svgpathtools)
* [cairoSVG](https://cairosvg.org/)
    NOTE: this lib has some quirks on Windows, which we resolve with including needed dlls in `./patttern/cairo_dlls` and adding the ditrectory to PATH in runtime
* [PySimpleGUI](https://github.com/PySimpleGUI/PySimpleGUI) to run GUI script
* wmi (on Windows)

All python dependencies can be installed with `pip install` / `conda install`:

```
conda create -n garmentcode python=3.9
conda activate garmentcode
pip install numpy scipy pyaml svgwrite psutil matplotlib svgpathtools cairosvg pysimplegui wmi
```

=> The code is ready to run

NOTE: 
* The dependency on [Pattern Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator) is included in the repo (`./external`), and will be loaded automatically by test script
* The environemtal variables needed for correct lib loading are set up in the test script

### Configuration of local paths

Same as here: https://github.com/maria-korosteleva/Garment-Pattern-Generator/blob/master/docs/Installation.md#local-paths-setup

NOTE: Currently, only the 'output' path is actually used, so it is enough to set up only 'output' parameter


## How to run (GUI)

From the root directory run
```
python gui.py
```

It can load body and design parameter files and display the corresponding sewing pattern right away.
Design files should be compatible with `MetaGarment` object (all examples provided in our supplementary materials are compatible, you can load `design_params.yaml` files).

### GUI: Notes on use

* The GUI was developed on Windows (11). All the libraries are cross-platform, but the tool was not tested under other OS and may behave unexpectedly.
* It is recommended to use high-resolution displays when using our GUI 
* Depending on your setup you might experience small lags in the interface responsiveness when working with patterns that have sleeves with curve-bases armhole. This is due to the need for solving optimization problems when working with such sleeves -- their implemetation is somewhat below realtime. 
    * If the lags are severe, we recommend to choose different armhole shape for sleeves as a workaround solution 

## How to run (command line)

Alternatively, one can use command line script to generate sewing patterns. From the root directory run
```
python test_garments.py
```

It will create sewing pattern for the current state of `assets/design_params/default.yaml` for average SMPL body, and put it to the logs folder. Modify the parameters inside the script as needed.


### Modifying the parameters
​
`./assets/design_params/default.yaml` contains the full set of style parameters for creating samples of our garment configurator.
​
* Update some of parameter values ('v:' field under parameter name) within a given range 
* run `test_garments.py` 
* `./Logs/default_<timestamp>` will contain the sewing patterns corresponding to given values
​
NOTE:
* The values of parameters are in cm (distances), degrees (angles), or given as a fraction
​
### Changing body measurements
​
To use another set of body measurements (among the ones used in the paper): 
 In `test_garments.py` change `body_to_use` variable to another key from `bodies_measurements` dictionary to use 
​
 * Options: 'avg', 'thin', 'fluffy', 'man'
 * Default: 'avg'  (=average female body shape)
​
The values for body measurements can be updated in corresponding configuration files (`./assets/body_measurements`)
​
Utilized examples for body shapes are given in `./assets/bodies` for reference.
## Attribution
We are using samples from [SMPL](https://smpl.is.tue.mpg.de/) body model as base for [Body Model examples](assets/Bodies). 
