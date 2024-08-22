# Installation

## Inslatting simulator

We use our own version of the [NVIDIA warp]() simulator. It should be installed manually to use our library correctly.

See the instructions in the repo: ()

## Using pip

With pip, you can install the core pygarment library and its dependencies to start writing your own garment programs!

```
pip install pygarment
```

## Manual Installation

If required, you could install the library and dependecies manually

### Install python with dependencies:

* Python 3.9
* numpy
* scipy
* pyyaml >= 6.0
* [svgwrite](https://pypi.org/project/svgwrite/)
* psutil
* matplotlib
* [svgpathtools](https://github.com/mathandy/svgpathtools)
* [cairoSVG](https://cairosvg.org/)
    NOTE: this lib has some quirks on Windows, which we resolve with including needed dlls in `./pygarment/pattern/cairo_dlls` and adding the ditrectory to PATH in runtime
* [NiceGUI](https://nicegui.io/#installation)
* wmi (on Windows)

All python dependencies can be installed with `pip install` / `conda install`:

```
conda create -n garmentcode python=3.9
conda activate garmentcode
<build and install warp for GarmentCode>
pip install numpy scipy pyaml svgwrite psutil matplotlib svgpathtools cairosvg nicegui wmi
```

=> The code is ready to run

> NOTE: 
> * The dependency on [Pattern Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator) is included in the repo (`./external`), and will be loaded automatically by test script
> * The environemtal variables needed for correct lib loading are set up in the test script

### Using as a library in other projects

Add the root repository to `PYTHONPATH`.

## (Optional) Installing Autodesk Maya+Qualoth garment viewer GUI

Our library serializes sewing patterns in a JSON format that extends the file format introduced in our previous project [Garment-Pattern-Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator/). GarmentCode supports the `garment_viewer` -- GUI extention for Maya that loads and simulated sewing patterns from JSON. To use this tool with GarmentCode patterns, follow the general installation steps from [Garment-Pattern-Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator/blob/master/docs/Installation.md), but use GarmentCode implementation of the libraries instead: 

> NOTE: Obtaning the code for Garment-Pattern-Generator is not needed.

1. Obtain Maya and Qualoth
1. Installing python libraries into python environment
1. (NEW!) Setup environment variables pointing to the `./pygarment` subdirectory of the GarmentCode repo  # TODO Check

