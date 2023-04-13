The contects of this directory are modified from the code of https://github.com/maria-korosteleva/Garment-Pattern-Generator (pattern package)

Additional dependencies introduced: 
* [svgpathtools](https://github.com/mathandy/svgpathtools)
* [cairoSVG](https://cairosvg.org/)
    NOTE: this lib has some quirks on Windows, which we relove with including needed dlls in `./patttern/cairo_dlls` and adding the ditrectory to PATH in runtime
* -svglib- removed!