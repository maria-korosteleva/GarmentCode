
# https://stackoverflow.com/questions/46265677/get-cairosvg-working-in-windows
# NOTE: I took the dlls from Inkscape
# NOTE: paths are relative to the running location, not to the current file
import os
if 'Windows' in os.environ.get('OS',''):
    os.environ['path'] += f';{os.path.abspath("./external/cairo_dlls")}'

import cairosvg
cairosvg.svg2png(url='gui/orig_shape.svg', write_to='gui/out_image.png', scale=5)