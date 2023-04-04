
# GarmentCode: Programming Parametric Sewing Patterns

Implementation of GarmentCode architecture and garment programs.

## Installation

Install python with dependencies:

* Python 3.9
* numpy
* scipy
* [svglib](https://pypi.org/project/svglib/)
* [svgwrite](https://pypi.org/project/svgwrite/)
* psutil
* matplotlib
* [bezier](https://bezier.readthedocs.io/en/stable/index.html)
* [svgpathtools](https://github.com/mathandy/svgpathtools)

#TODO one of the latter too will be used in the final version

All python dependencies can be installed with `pip install` / `conda install`

=> The code is ready to run

NOTE: 
* The dependency on [Pattern Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator)in included in the repo (`./external`), and will be loaded automatically by test script
* The environemtal variables needed for correct lib loading are set up in the test script

## How to run

From the root directory run
```
test_garments.py
```

It will create sewing patterns for histrical dresses used in a teaser of our paper fitted to the average SMPL body model (female).

The rusuts are saved to `./Logs` folder

## Modifying the parameters

`./assets/design_params/base.yaml` contains the full set of style parameters for creating samples of our garment configurator.

* Update some of parameter values ('v:' field under parameter name) withing a given range 
* run `test_garments.py` 
* `./Logs/base_<timestamp>` will contain the sewing patterns corresponding to given values


## Attribution
We are using samples from [SMPL](https://smpl.is.tue.mpg.de/) body model as base for [Body Model examples](assets/Bodies). 
