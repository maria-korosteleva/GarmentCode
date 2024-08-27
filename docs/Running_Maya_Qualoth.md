# Running simulation of GarmentCode patterns in Autodesk Maya + Qualoth

GarmentCode serializes sewing patterns in a JSON format that extends the file format introduced in our previous project [Garment-Pattern-Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator/). We modified the corresponding tools for Autodesk Maya & Qualoth to support the GUI designed for an pipeline.

## Installing dependecies

> NOTE: Obtaning the code for Garment-Pattern-Generator is not needed.

1. Install Maya and Qualoth
1. Install `pygarment` into Maya python environment following the [Installation instructions for python packages for Maya](https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2022/ENU/Maya-Scripting/files/GUID-72A245EC-CDB4-46AB-BEE0-4BBBF9791627-htm.html). This will look something like this: 

    ```
    mayapy -m pip install pygarment
    ```

    > NOTE: since Maya UI won't use warp simulator and use Qualoth simulation instead, installing warp is not necessary


## Running GarmentViewer

GarmentCode supports the `garment_viewer` -- GUI script for Maya that loads and simulated sewing patterns from JSON. 

To use it, simply run Autodesk Maya and copy the contents of `./gui/maya_garmentviewer.py` to the Python scripting console.

For more info on the GUI, check our precious project docs: [Garment Viewer](https://github.com/maria-korosteleva/Garment-Pattern-Generator/blob/master/docs/Setting_up_generator.md#preview-your-setup-in-garmentviewer-gui)


### Material properties

Material properties for garment simulation (in Garment Viewer) that were used for the figures in the GarmentCode paper are located in [assets/Sim_props](../assets/Sim_props)