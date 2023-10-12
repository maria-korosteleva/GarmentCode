import os
import sys

# Makes core library available without extra installation steps
sys.path.insert(0, './external/')
sys.path.insert(1, './')

# Custom
from gui.callbacks import GUIState

if 'Windows' in os.environ.get('OS',''):
    # https://stackoverflow.com/a/43046744
    # Resolwing blurry fonts on Windows
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)

if __name__ == '__main__':

    state = GUIState()

    state.event_loop()

    del state
    