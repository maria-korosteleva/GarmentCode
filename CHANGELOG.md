
# Change Log

## [2.0.0] - 2024-08-30
 
Major update with release of [GarmentCodeData](https://igl.ethz.ch/projects/GarmentCodeData/), new GUI, and a number of other improvements and library changes. For technical details, see our papers.


### Added
- **[Mesh generation]** GarmentCode library can now generate box meshes for the sewing patterns.
- **[Simulation]** We integrated our version of [NVIDIA warp]() # TODO UPD to support simulation of GarmentCode sewing patterns. It can be run from command line and from GUI.
- **[Desing Sampling]** We support random sampling of sewing pattern designs from the designs spaces. Sampling can be controlled though setting probabilities of sampling default values.
- **[Generating synthetic 3D data]** Combining the new capabilities allows for creating diverse synthetic datasets of 3D garments. We provide high-level scripts to create such datasets from the GarmentCode-provided garment programs.
- **[Labeling]** We added support for assigning labels to pattern elements (edges and panels) in both GarmentCode objects and JSON serialized pattern representation. These are currently utilized to guide the cloth simulation process, but can be assigned to enrich the data labeling.
- **[Stitch orientation]** GarmentCode now allows explicit specification of whether a stitch should be connecting the right side of the fabric on one side to the right side of the fabric on the other or right side to wrong side. It gives explicit control to developer on resolving the stitching direction. Most stitches require the default (right-to-right) setting, hence only a few need explicit update of this parameter. Internally, the right-to-right direction is found following the manifold property of connecting two panels with specified normal direction indicating the right side of the fabric. 

### Changed
- **[Architecture]** We updated the structure of `pygarment` library. It now includes new mesh generation and cloth simulation routines, as well as the pattern serialization modules (`pattern` library) and the Maya + Qualoth routines for backward compatibility. This greatly simplifies the installation process and reduces module import issues.  
- **[GUI]** We re-wrote our GUI from PySimpleGUI to NiceGUI following the change in PySimpleGUI licensing scheme and desire for better UI look. GarmentCode GUI now runs in browser. Dependency on PySimpleGUI is removed.
- **[Interface matching]** In addition to stitch orientation labels above, we removed extra heuristics involved in the matching of the edges in two interfaces connected by a stitch. We found that these heuristics behaved unintuitively in some cases, and it was difficult to determine the correct way to fix erroneous matched. The process is now fully controlled by the developer, making it more intuitive. As before, the default matching process should work in most cases, and only a few complex stitches require intervention.
 
### Fixed
- **[Sewing patterns quality]** We have made numerous improvements to the quality of sewing patterns produced by our garment programs. They now showcase better fit, balance and 3D alignment
- **[Design space]** We have updated the quality of the parameter interaction in our garment programs introducing better parameter ranges, parameter dependencies, interaction between design and body shape parameters, etc. Design space now has fewer invalid parameter combinations making the exploration of parameter space more reliable. 
- **[Other]** numerous small bugs where discovered and fixed.

 
## [1.0.0] - 2023-10-18
 
Initial release -- implemetation of [GarmentCode](https://igl.ethz.ch/projects/garmentcode/)