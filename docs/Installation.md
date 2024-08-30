# Installation

## Local paths setup 

Create system.json file in the root of this directory with your machine's file paths using `system.template.json` as a template. 
`system.json` should include the following: 
* Path for creating logs for one-off scripts (`'output'`)
* Path to the folder with (generated) datasets of sewing patterns (`'datasets_path'`)
* Path to the folder with simulation results on the datasets of sewing patterns (`'datasets_sim'`)

* Data generation & Simulation resources  
    * path to folder with simulation\rendering configurations (`'sim_configs_path'`)
    * path to folder containing body files for neutral body and other base body models (`'bodies_default_path'`)
    * path to folder containing datasets of body shape samples (`'body_samples_path'`)
    

## Installing simulator

We use our own version of the [NVIDIA warp](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode) simulator. It should be installed manually to use our library correctly.

See the instructions in the [NvidiaWarp-GarmentCode](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode) repo. 

## Using pip

With pip, you can install the core pygarment library and its dependencies to start writing your own garment programs!

```
pip install pygarment
```

## Manual Installation

If required, you could install the library and dependecies manually

### Install python with dependencies:

* Python 3.9
* numpy<2
* scipy
* pyyaml >= 6.0
* [svgwrite](https://pypi.org/project/svgwrite/)
* psutil
* matplotlib
* [svgpathtools](https://github.com/mathandy/svgpathtools)
* [cairoSVG](https://cairosvg.org/)
    NOTE: this lib has some quirks on Windows, which we resolve with including needed dlls in `./pygarment/pattern/cairo_dlls` and adding the ditrectory to PATH in runtime
* [NiceGUI](https://nicegui.io/#installation)
* [trimesh](https://trimesh.org/)
* [libigl](https://libigl.github.io/libigl-python-bindings/)
* [pyrender](https://pyrender.readthedocs.io/en/latest/index.html)
* [CGAL](https://pypi.org/project/cgal/)

All python dependencies can be installed with `pip install` / `conda install`:

```
conda create -n garmentcode python=3.9
conda activate garmentcode
pip install numpy<2 scipy pyaml>=6.0 svgwrite psutil matplotlib svgpathtools cairosvg nicegui trimesh libigl pyrender cgal
<build and install warp for GarmentCode>
```

Add the root repository to `PYTHONPATH`.

=> The code is ready to run
