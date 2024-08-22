# Running GarmentCode Configurator 

## How to run (GUI)

From the root directory run
```
python gui.py
```

It will launch a local version of GarmentCode web-interface. 

GUI can load body and design parameter files and display the corresponding sewing pattern right away, as well as display draped 3D models.
Design files should be compatible with `MetaGarment` object (all examples provided [assets/design_params/](../assets/design_params) are compatible).

### GUI: Notes on use

* It is recommended to use high-resolution displays when using our GUI 
* Depending on your setup you might experience small lags in the interface responsiveness. This is due to the need for solving optimization problems when working with some of garment elements, e.g. sleeve curve inversion -- their implemetation is somewhat below realtime. 
    * If the lags are severe, we recommend to choose a different armhole shape for sleeves as a workaround solution. 

## How to run GarmentCode (command line)

Alternatively, one can use command line script to create sewing patterns from design and body parameters. From the root directory run
```
python test_garmentcode.py
```

It will create sewing pattern for the current state of `assets/design_params/default.yaml` for neutral body, and put it to the logs folder. Modify the parameters inside the script as needed.


### Modifying the parameters
​
[assets/design_params/default.yaml](../assets/design_params/default.yaml) contains the full set of style parameters for creating samples of our garment configurator.
​
* Update some of parameter values ('v:' field under parameter name) within a given range 
* run `test_garmentcode.py` 
* `./Logs/default_<timestamp>` will contain the sewing patterns corresponding to given values
​
NOTE:
* The values of parameters are in cm (distances), degrees (angles), or given as a fraction
​
### Changing body measurements

# TODO Update with the new script
To use another set of body measurements (among the ones used in the paper): 
 In `test_garmentcode.py` change `body_to_use` variable to another key from `bodies_measurements` dictionary to use 
​
 * Options: 'avg', 'thin', 'full-bodied', 'man'
 * Default: 'avg'  (=average female body shape)
​

The values for body measurements can be updated in corresponding configuration files (`./assets/body_measurements`). 
​
Utilized examples for body shapes are given in `./assets/bodies` for reference.

> NOTE: Descriptions of body measurements are provided in  [docs/Body Measurements GarmentCode.pdf](Body%20Measurements%20GarmentCode.pdf).


## How to simulate patterns (command line)

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
   

