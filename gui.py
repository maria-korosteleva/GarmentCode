import os
import sys
from pathlib import Path
sys.path.append(str((Path(os.getcwd()) / 'external').resolve()))
from gui.callbacks_psg import GUIState

if 'Windows' in os.environ.get('OS', ''):
    # https://stackoverflow.com/a/43046744
    # Resolwing blurry fonts on Windows
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)

# TODO Instructions
# TODO Post screenshots here: https://github.com/PySimpleGUI/PySimpleGUI/issues/10
# after publication =)

if __name__ == '__main__':

    state = GUIState()
    state.event_loop()
    del state
    