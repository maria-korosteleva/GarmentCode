
# GarmentCodeData: Running data generation and simulation

GarmentCode now supports a synthetic data generation pipeline of [GarmentCodeData](https://igl.ethz.ch/projects/GarmentCodeData/) using [our fork of NVIDIA Warp simulator](https://github.com/maria-korosteleva/NvidiaWarp-GarmentCode). For the technical details of the generation process, please, check the paper.

The default setup creates sewing pattern samples based on the [garment programs](../assets/garment_programs/) provided in this repo with sampling probabilities specified in [assets/design_params/default.yaml](../assets/design_params/default.yaml). 

Simulation process is controlled by a configuration file (see below), specifying material properties and other simulation and rendering hyperparameters.

The generation pipline consists of two steps that need to be run sequentially:

* Sampling sewing pattern designs from template 
* Draping each over the base body (physics simulation)

More on each step below.

## Preparation
Before generating garment data, make sure to 

* Obtain dataset of sample body shapes, either by downloading it from GarmentCodeData, or by creating your own sample using [our tool](https://github.com/mbotsch/GarmentMeasurements).
* Setup the paths `system.json` as described in [Installation](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Installation.md).
* Customize the parameter ranges and probabilities as suits your application, following the example of [assets/design_params/default.yaml](../assets/design_params/default.yaml) 
    > Example: to restrict the design space to upper garments only, set the default value for bottoms (`design['meta']['bottom']['v']`) to `null` and `defaul  t_prob` to 1.0 (`design['meta']['bottom']['defaul  t_prob']`).
* Customize simulation config (see below for details).

## Sewing pattern sampling 
`pattern_sampler.py` script generates 2D pattern samples from GarmentCode parametric garment programs and a body shape dataset. The tool will produce design samples each fitted to a neutral body shape and a random shape sample. By default,
* It looks for `5000_body_shapes_and_measures` folder in system['bodies_default_path'] for the body samples.
* It uses [assets/design_params/default.yaml](../assets/design_params/default.yaml) as a source of design parameter set, ranges and associated probabilites.

To use different body set or design parameter file, update the script as needed.

To start generating, simply specify desired dataset name and size : 

```
python pattern_sampler.py --name garmentcodedata --size 100
```

One can also specify batch id, which is simply adds a modifier to the specifies dataset name, but was proved useful for parallel generation of data in batches: 

```
python pattern_sampler.py --name garmentcodedata --size 100 --batch_id 0
```

### Replicating existing data batch

The tool supports replication of the existing datasets. It will find the dataset in system['datasets'] folder and re-sample it from the same random seed. For that simply specify the name of the dataset to replicate:
```
python pattern_sampler.py --replicate garments_5000_0 
```

### Fitting one design to a selection of body shapes

`pattern_fitter.py` script allows fixing the design (though fixing design parameters) and vary only the body shapes while creating sewing patterns. Fit to the neutral body shape is also created. The output follows the same folder structure as the regular sampling. 

To start fitting, simply specify desired design parameter file to fit, dataset name and size: 

```
python pattern_fitter.py .\assets\design_params\t-shirt.yaml --name t-shirt-fit --size 100
```

The name of the body shape set can be specified inside the script (defaults to out sample `5000_body_shapes_and_measures`).

> Important: the selection of body shapes is NOT RANDOMIZED. The script tranverses the bodies in the specified sample one by one in aphabetical order

## Simulation
`pattern_data_sim.py` script simulates each pattern in the provided dataset of sewing patterns. 

The basic parameters of the script include:
* `data` -- the name of the sewing patterns dataset located in system['datasets_path']
* `config` -- path to simulation config file (see below for details)

To run the draping of all the design samples fitted to a neutral body, use the `--default_body` flag. 
```
python ./pattern_data_sim.py --data garmentcodedata --config /path/to/sim_config --default_body
```

When the flag is omitted, the pipeline will process the portion of the dataset where the designs are fitten to random body shapes:
```
python ./pattern_data_sim.py --data garmentcodedata --config /path/to/sim_config
```

### Running simulation of in batches


Simulation process support resuming: it can be stopped and continued at any moment, picking up from where it left off. The required information is stored in `dataset_properties_<tag>.yaml` file in the output folder. 

The command like has a `minibatch` parameter that specifies the number of samples to simulate before exiting the script (by default, the full dataset is processed):

```
python ./pattern_data_sim.py --data garmentcodedata --config /path/to/sim_config --minibatch 100
```

This becomes useful when running simulation of large datasets on remote server since the data can be produced and transferred over the network in small portions. 

`pattern_data_sim_runner.sh`:

By putting additional time contraints on batch processing, one can detect hangs or script crushes and automatically resume the processing on the rest of the datapoints, as implemented the `pattern_data_sim_runner.sh` shell script


### Simulation config file

Config file has a similar structure to the one used in our previous project [Garment-Pattern-Generator](https://github.com/maria-korosteleva/Garment-Pattern-Generator/). 

> Any `dataset_properties_<tag>.yaml` file of existing datasets could be used in place of Simulaiton Config file. This is an easy way to reproduce simulation and rendering context of existing data. It also stores random seed for sewing pattern sampler making it reproducible as well. 

[`data_generation/Sim_props`](../data_generation/Sim_props) contains configuration for dataset simulation process.

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

> Simulation parameters differ significantly for Warp-based and Qualoth-based piplines, and they cannot be used interchengeably.






