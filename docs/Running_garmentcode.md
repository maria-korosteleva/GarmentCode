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
* All the 3D drapes are currently fitted to a neutral body model with the current design parameters. 
* [assets/design_params/default.yaml](../assets/design_params/default.yaml)  is the setup used by GUI on load. Changing this file results in changes in the GUI initial state =)

## How to run GarmentCode (command line)

Alternatively, one can use command line script to create sewing patterns from design and body parameters. From the root directory run
```
python test_garmentcode.py
```

It will create sewing pattern for the current state of `assets/design_params/t-shirt.yaml` for neutral body, and put it to the logs folder. Modify the parameters inside the script as needed.


### Modifying the parameters
​
[assets/design_params/t-shirt.yaml](../assets/design_params/t-shirt.yaml) contains the full set of style parameters for creating samples of our garment configurator.
​
* Update some of parameter values ('v:' field under parameter name) within a given range 
* run `test_garmentcode.py` 
* `system['output']/t-shirt_<timestamp>/` will contain the sewing patterns corresponding to given values
​
NOTE:
* The values of parameters are in cm (distances), degrees (angles), or given as a fraction
​
### Changing body measurements

To use another set of body measurements (among the ones used in the paper): 
 In `test_garmentcode.py` change `body_to_use` variable to another key from `bodies_measurements` dictionary to use 
​
 * Options: 'neutral', 'mean_female', 'mean_male', 'f_smpl', 'm_smpl'
 * Default: 'neutral'  (=gender neutral average body shape)
​

The values for body measurements can be updated in corresponding configuration files (`./assets/body_measurements`). 
​
Utilized examples for body shapes are given in `./assets/bodies` for reference.

> NOTE: Descriptions of body measurements are provided in  [docs/Body Measurements GarmentCode.pdf](Body%20Measurements%20GarmentCode.pdf).


## How to simulate patterns (command line)

One can use a python script to drape a sewing pattern in JSON representation, produced by GarmentCode:  

```
python test_garment_sim.py -p /path/to/pattern_specification.json -s /path/to/sim_props.json
```

The result is saved to `'output'` folder, specified in `system.json` file.

By default, it drapes the pattern over the neutral body model. The body model and verbose levels can be updated inside the `test_garment_sim.py` script.



