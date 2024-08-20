
# GarmentCode: Programming Parametric Sewing Patterns

Implementation of GarmentCode architecture and garment programs.

## Installation

### Install python with dependencies:

* Python 3.9 or 3.11
* numpy
* scipy
* [svgwrite](https://pypi.org/project/svgwrite/)
* psutil
* matplotlib
* [svgpathtools](https://github.com/mathandy/svgpathtools)
* [cairoSVG](https://cairosvg.org/)
    NOTE: this lib has some quirks on Windows, which we relove with including needed dlls in `./external/cairo_dlls` and adding the ditrectory to PATH in runtime
* [PySimpleGUI](https://github.com/PySimpleGUI/PySimpleGUI) to run GUI script

All python dependencies can be installed with 

```
conda env create -f environment.yml
```
or 

```
pip install -r requirements.txt
```

NOTE: 
* The dependency on [Pattern Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator) is included in the repo (`./external`), and will be loaded automatically by test script
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


## TODO

### Notes
* cairo_dlls windows

### Installation for Maya
The contects of this directory are modified from the code of https://github.com/maria-korosteleva/Garment-Pattern-Generator (pattern package)

Add current directory (`./external`) to PYTHONPATH for Maya to use this version when loading garment viewer or running batch sumulation. 

The entry script for garment viewer is the same as in the original project and can be taken from there.

Additional dependencies in this version: 
* [svgpathtools](https://github.com/mathandy/svgpathtools)
* [cairoSVG](https://cairosvg.org/)
    NOTE: this lib has some quirks on Windows, which we relove with including needed dlls in `./external/cairo_dlls` and adding the ditrectory to PATH in runtime
* -svglib- removed!

These are need to be installed in Maya Python with the rest of the libs from original project.

## Instructions from old sim repo

Run mesh generation, simulation and image rendering of a pattern:
--------------------------------------------------------------------
1. Put your pattern .json file into: "meshgen > assets > Patterns" folder and please name the json file such that it ends with "_specification.json" (e.g. "dress_specification.json)

2. Open garment_gen_sim.py:
   - Adapt the garment_name (line 66) to your garment name (without "_specification": e.g. "dress")
   - Set appropriate body_name: default is ['non_centered','f_average_A40']
     -> use 'centered' for an old data sample, i.e. if the body is centered at the origin
     -> models: "f_average_A40", "m_average_A40", "f_model_A40", "f_fluffy_A40", "f_smpl_template" 
     -> for a custom model, place it into the "meshgen > assets > Bodies > centered or uncentered" folder

3. Run garment_gen_sim.py:
   - See the output in the "output" folder :)
     -> panels: .obj file of each panel
     -> simulation: 
        - "body.obj" (body as .obj file)
        - the .png renders
        - "...-simulated.obj" (simulated cloth as .obj file) 
        - "...-simulation.usd" (simulation file, can be viewed in Blender or Omniverse Create XR)
           -> "meshgen > gui > blenderGUI.blend" displays simulation with segmentation 
              (see instructions in Scripting window)
   



Run dataset:
-------------
1. Generate your dataset
2. In datasim.py change the path_to_Proc_Garm (line 44) to your Procedural Garment root directory and run it with 
   --data "name of your dataset" (e.g. --data data_40_230829-11-07-59)
3. Ouput: See the output in the "dataset_properties.yaml file" in the folder of your dataset


To metion:
------------
1. using trimesh lib to load garments with textures
   ```
   print('Reloading exported ply ', path_to_out)
   mesh_again: trimesh.Trimesh = trimesh.load_mesh(path_to_out, process=False)
   # 
   print(mesh_again.visual.uv.shape, type(mesh_again.visual))

   tex_image = PIL.Image.open(tex_path)
   tex = trimesh.visual.TextureVisuals(mesh_again.visual.uv, image=tex_image)
   mesh_again.visual = tex

   mesh_again.show()
   ```
1. How to restore the texture used in the data renders from the optimized version

1. trimesh issue with the vertex duplication https://github.com/mikedh/trimesh/issues/1057

```
def v_id_map(vertices):
    v_map = [None] * len(vertices)
    v_map[0] = 0
    for i in range(1, len(vertices)):
        v_map[i] = v_map[i-1] if all(vertices[i - 1] == vertices[i]) else v_map[i-1] + 1
    return v_map
```