# GarmentCode: Programming Parametric Sewing Patterns

![Examples of garments sampled from GarmentCode configurator](https://github.com/maria-korosteleva/GarmentCode/raw/main/assets/img/header.png)

Official Implementation of [GarmentCode: Programming Parametric Sewing Patterns](https://igl.ethz.ch/projects/garmentcode/) and [GarmentCodeData: A Dataset of 3D Made-to-Measure Garments With Sewing Patterns](https://igl.ethz.ch/projects/GarmentCodeData/).

## News

**[Aug XX, 2024]** Major release -- implementation of [GarmentCodeData](https://igl.ethz.ch/projects/GarmentCodeData/), new GUI, and other updates and improvements. Basic JSON representation classes are now part of PyGarment library! See CHANGELOG for more details

**[Aug XX, 2024]** New dataset version of the [GarmentCodeData]() is released!

**[July 1, 2024]** [GarmentCodeData](https://igl.ethz.ch/projects/GarmentCodeData/) is accepted to ECCV!

**[Oct 18, 2023]** First release of GarmentCode!

## Documents

1. [Installation](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Installation.md)
2. [Running Configurator](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Running_garmentcode.md) 
3. [Running Data Generation (warp)](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Running_data_generation.md) 
3. [Body measurements](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Body%20Measurements%20GarmentCode.pdf)
4. [Dataset documentation]() # TODO add with new link
3. [Running Old Maya+Qualoth tools](https://github.com/maria-korosteleva/GarmentCode/blob/main/docs/Running_Maya_Qualoth.md) 

## Navigation

### Library

[PyGarment](https://github.com/maria-korosteleva/GarmentCode/tree/main/pygarment) is the core library described in the GarmentCode paper. It contains the base types (Edge, Panel, Component, Interface, etc.), as well as edge factory and various helpers and operators that help you design sewing patterns.  

See [Installation instructions](https://github.com/maria-korosteleva/GarmentCode/tree/main/docs/Installation.md) before use.

### Examples

* [assets/garment_programs/](https://github.com/maria-korosteleva/GarmentCode/tree/main/assets/garment_programs/) contains the code of garment components designed using PyGarment. 
* [assets/design_params/](https://github.com/maria-korosteleva/GarmentCode/tree/main/assets/design_params/), [assets/bodies/](https://github.com/maria-korosteleva/GarmentCode/tree/main/assets/bodies/) contain examples of design and body measurements presets. They can be used in both GarmentCode GUI and `test_garmentcode.py` script.

> NOTE: [assets/design_params/default.yaml](https://github.com/maria-korosteleva/GarmentCode/blob/main/assets/design_params/default.yaml) is the setup used by GUI on load. Changing this file results in changes in the GUI initial state =) 


## Citation

If you are using our system in your research, please cite our papers:

```
@inproceedings{GarmentCodeData:2024,
  author = {Korosteleva, Maria and Kesdogan, Timur Levent and Kemper, Fabian and Wenninger, Stephan and Koller, Jasmin and Zhang, Yuhan and Botsch, Mario and Sorkine-Hornung, Olga},
  title = {{GarmentCodeData}: A Dataset of 3{D} Made-to-Measure Garments With Sewing Patterns},
  booktitle={Computer Vision -- ECCV 2024},
  year = {2024},
  keywords = {sewing patterns, garment reconstruction, dataset},
}
```

```
@article{GarmentCode2023,
  author = {Korosteleva, Maria and Sorkine-Hornung, Olga},
  title = {{GarmentCode}: Programming Parametric Sewing Patterns},
  year = {2023},
  issue_date = {December 2023},
  publisher = {Association for Computing Machinery},
  address = {New York, NY, USA},
  volume = {42},
  number = {6},
  doi = {10.1145/3618351},
  journal = {ACM Transaction on Graphics},
  note = {SIGGRAPH ASIA 2023 issue},
  numpages = {16},
  keywords = {sewing patterns, garment modeling}
}
```

## Issues, questions, suggestions

Please post your issues and questions to [GitHub Issues](https://github.com/maria-korosteleva/GarmentCode/issues).

For other requests you can find my info on https://korosteleva.com/.  


## Attribution & Body use disclaimer  # TODO Update
We are using samples from [SMPL](https://smpl.is.tue.mpg.de/) body model as base for [Body Model examples](https://github.com/maria-korosteleva/GarmentCode/tree/main/assets/Bodies). 

### Disclaimer
Due to the restrictions of the SMPL license, we cannot share all 3D models of the body shapes used in our paper, except for the base average bodies for male and female versions of SMPL. We nevertheless share the approximate body measurements of the thin and the full-bodied models to showcase the adaptation of the patterns to different body types. 
