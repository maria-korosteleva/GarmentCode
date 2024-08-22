
# GarmentCodeData: Running data generation and simulation

GarmentCode now supports a synthetic data generation pipeline of [GarmentCodeData](https://igl.ethz.ch/projects/GarmentCodeData/) using [our fork of NVIDIA Warp simulator](). For the technical details of the generation process, please, check the paper. 

The default setup creates sewing pattern samples based on the [garment programs](../assets/garment_programs/) provided in this repo with sampling probabilities specified in [assets/design_params/default.yaml](../assets/design_params/default.yaml). 

Simulation process is controlled by a configuration file (see below), specifying material properties and other simulation and rendering hyperparameters.

The generation pipline consists of two steps that need to be run sequentially:

* Sampling sewing pattern designs from template 
* Draping each over the base body (physics simulation)

More on each step below.


## Dataset generator
`pattern_sampler.py` script

2D pattern dataset generation from given templates. Allows to configure the generation by supplying Properties object.
Example usage of the generator is given in 
``` if __name__ == "__main__": ```
section of the file.

## Simulation
`pattern_data_sim.py` script  # TODO type of the body!!!

* Simulates each pattern in the dataset over a given human body object
* Uses Qualoth for Maya cloth simulation
* It is designed to run with Mayapy as standalone interpreter 
* Command line arguments are the dirs\files basenames given that system.json is properly created.

Example usage from command line:
```
<Maya Installation path>/bin/mayapy.exe "./datasim.py" --data <dataset_name> --minibatch <size>  --config <simulation_props.json>
```

## Simulation config file

Config file has a similar structure to the one used in our previous project [Garment-Pattern-Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator/). 

> Any `dataset_properties_<tag>.yaml` file of existing datasets could be used in place of Simulaiton Config file. This is an easy way to reproduce simulation and rendering context of existing data. It also stores random seed for sewing pattern sampler making it reproducible as well. 

[`data_generation/Sim_props`](../data_generation/Sim_props) contains configuration for dataset simulation process.

> Simulation parameters differ significantly for Warp-based and Qualoth-based piplines, and they cannot be used interchengeably.

On the high level, every config contains the following

* Material properties of garment fabric & body to be used for physics simulation
* Geometry resolution scale (correspoding to average edge size in generated garment meshes)
* Different thresholds to control the sensitivity of simulation quality checks
    * Simulation quality checks are designed to filter out garments with failed simulations to avoid biasing the training a dataset will be used for
    * Examples of bad simulation results: skirt sliding down to the legs; heavy self-intersections, etc.
* Render setup with the following elements: 
    * a desired resulution of output images
    * Texturing parameters
    * Camera location for the front view

Simulation process support resuming: it can be stopped and continued at any moment, picking up from where it left off. The required information is stored in `dataset_properties_<tag>.yaml` file in the output folder.

#### **Running simulation of in batches**

`pattern_data_sim_runner.sh` script is given for convence of processing large amounts of garment patterns over long period of time. The main feature is detection of dataset sim processing hangs \ crashes and automatic resume of dataset processing in case of such events. 


