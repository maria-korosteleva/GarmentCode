import os
import sys
from pathlib import Path
sys.path.append(str((Path(os.getcwd()) / 'external').resolve()))
# DRAFT from gui.callbacks_psg import GUIState
from gui.callbacks import GUIState

# TODO Probably not needed for NiceGUI?
if 'Windows' in os.environ.get('OS', ''):
    # https://stackoverflow.com/a/43046744
    # Resolwing blurry fonts on Windows
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)

# TODO Instructions

if __name__ == '__main__':

    state = GUIState()
    state.run()
    del state
    