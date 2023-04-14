import os
# Custom
from gui.callbacks import GUIState

if 'Windows' in os.environ.get('OS',''):
    # https://stackoverflow.com/a/43046744
    # Resolwing blurry fonts on Windows
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)

# TODO Instructions

if __name__ == '__main__':

    state = GUIState()

    state.event_loop()

    del state
    