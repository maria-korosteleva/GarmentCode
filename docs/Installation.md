# Installation Instructions

## Dependencies

* Autodesk Maya 2022+ with Arnold
    >☝ Arnold requires license to render simulated data without watermarks.

* [Qualoth](http://www.fxgear.net/vfx-software?locale=en), versiton 4.7.7+ (with Maya 2022 support)
### Python Environment (both in Maya Python Environment, and for usual development)

[Installation instructions for python packages for Maya](https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2022/ENU/Maya-Scripting/files/GUID-72A245EC-CDB4-46AB-BEE0-4BBBF9791627-htm.html)

* numpy
* scipy
* [svglib](https://pypi.org/project/svglib/)
* [svgwrite](https://pypi.org/project/svgwrite/)
* psutil
* wmi
    * May require pypiwin32
    * [Troubleshooting 'DLL load failed while importing win32api'](https://stackoverflow.com/questions/58612306/how-to-fix-importerror-dll-load-failed-while-importing-win32api) error on Win


<details>
    <summary> <b>NOTE: Lib versions used in development</b></summary>
    python==3.8.5
    numpy==1.19.2
    scipy==1.6.2
    svglib==1.0.1
    svgwrite==1.4
    psutil==5.7.2
    wmi=1.5.1
</details>

## Setting up 
### Environmental variables

* Add `./packages` to `PYTHONPATH` on your system for correct importing of our custom modules.
### Local paths setup

Create system.json file in the root of this directory with your machine's file paths using `system.template.json` as a template. 
`system.json` should include the following: 
* Path for creating logs at (including generated data from dataset generation routined & NN predictions) (`'output'`)
* Path to the folder with (generated) garment datasets (`'datasets_path'`)

* Data generation & Simulation resources  (default to subdirectories of `./data_generation`)
    * path to pattern templates folder (`'templates_path'`) 
    * path to folder containing body files (`'bodies_path'`)
    * path to folder containing render scenes (`'scenes_path'`)
    * path to folder with simulation\rendering configurations (`'sim_configs_path'`)