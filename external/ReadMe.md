The contects of this directory are modified from the code of https://github.com/maria-korosteleva/Garment-Pattern-Generator (pattern package)

Add current directory (`./external`) to PYTHONPATH for Maya to use this version when loading garment viewer or running batch sumulation. 

The entry script for garment viewer is the same as in the original project and can be taken from there.

Additional dependencies in this version: 
* [svgpathtools](https://github.com/mathandy/svgpathtools)
* [cairoSVG](https://cairosvg.org/)
    NOTE: this lib has some quirks on Windows, which we relove with including needed dlls in `./patttern/cairo_dlls` and adding the ditrectory to PATH in runtime
* -svglib- removed!

These are need to be installed in Maya Python with the rest of the libs from original project.