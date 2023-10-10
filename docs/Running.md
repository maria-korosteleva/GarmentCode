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
    * If the lags are severe, we recommend to choose a different armhole shape for sleeves as a workaround solution. 

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

## Running GarmentViewer to simulate created patterns

Our library serializes sewing patterns in a JSON format that extends the file format introduced in our previous project [Garment-Pattern-Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator/). GarmentCode supports the `garment_viewer` -- GUI script for Maya that loads and simulated sewing patterns from JSON. 

!! Important !! Check the instructions for [Installation](docs/Installation.md).

Using this tool is exactly the same as in the original project, follow the instrustions here: [Garment Viewer](https://github.com/maria-korosteleva/Garment-Pattern-Generator/blob/master/docs/Setting_up_generator.md#preview-your-setup-in-garmentviewer-gui)


### Material properties

Material properties for garment simulation (in Garment Viewer) that were used for the figures in the paper are located in [assets/Sim_props](assets/Sim_props)