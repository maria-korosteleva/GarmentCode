# Installation

## Install python with dependencies:

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

> NOTE: 
> * The dependency on [Pattern Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator) is included in the repo (`./external`), and will be loaded automatically by test script
> * The environemtal variables needed for correct lib loading are set up in the test script

## Configuration of local paths

Same as here: [Garment-Pattern-Generator/Installation](https://github.com/maria-korosteleva/Garment-Pattern-Generator/blob/master/docs/Installation.md#local-paths-setup)

NOTE: Currently, only the 'output' path is actually used, so it is enough to set up only 'output' parameter

## Using as a library in other projects

Add GarmentCode repository to `PYTHONPATH`.

> NOTE: We do not currently have installation script or pip package for PyGarment. Contributions are welcomed!

## (Optional) Installing Autodesk Maya+Qualoth garment viewer GUI

Our library serializes sewing patterns in a JSON format that extends the file format introduced in our previous project [Garment-Pattern-Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator/). GarmentCode supports the `garment_viewer` -- GUI extention for Maya that loads and simulated sewing patterns from JSON. To use this tool with GarmentCode patterns, follow the general installation steps from [Garment-Pattern-Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator/blob/master/docs/Installation.md): 

> NOTE: Obtaning the code for Garment-Pattern-Generator is not needed.

1. Obtain Maya and Qualoth
1. Installing python libraries into python environment
1. Setup environment variables (NEW!) pointing to the `./external` subdirectory of the GarmentCode repo

