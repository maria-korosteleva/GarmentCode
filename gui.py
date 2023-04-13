import PySimpleGUI as sg
import numpy as np

# Custom
from gui.callbacks import State

# NOTE: PySimpleGUI reference: https://github.com/PySimpleGUI/PySimpleGUI/blob/master/docs/call%20reference.md

# TODO Instructions
# TODO allow changing window size? https://stackoverflow.com/questions/66379808/how-do-i-respond-to-window-resize-in-pysimplegui
# https://stackoverflow.com/questions/63686020/pysimplegui-how-to-achieve-elements-frames-columns-to-align-to-the-right-and-r
# TODO Visual appearance
# https://github.com/PySimpleGUI/PySimpleGUI/issues/3412 for nice buttons & stuff
# Native demo https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Simple_Material_Feel.py
# TODO Icons

pattern_state = State()
canvas_margins = [20, 20]
body_img_id = None
back_img_id = None
window = None

def def_layout(canvas_size=(500, 500)):

    # First the window layout in 2 columns

    params_column = [
        [
            sg.Text('Body Mesurements: '),
        ],
        [
            sg.In(
                default_text=pattern_state.body_file,
                size=(25, 1), 
                enable_events=True, 
                key='-BODY-'
            ),
            sg.FileBrowse(),
        ],
        [
            sg.Text('Design parameters: '),
        ],
        [
            sg.In(
                default_text=pattern_state.design_file,
                size=(25, 1), 
                enable_events=True, 
                key='-DESIGN-'
            ),
            sg.FileBrowse(),
        ],
    ]

    # For now will only show the name of the file that was chosen
    viewer_column = [
        [sg.Graph(
            canvas_size=canvas_size, 
            graph_bottom_left=(0, canvas_size[1]), 
            graph_top_right=(canvas_size[0], 0), 
            background_color='white', 
            key='-CANVAS-')
        ],      
        [
            sg.Text('Output Folder:'),
            sg.In(
                default_text=pattern_state.save_path, 
                expand_x=True, 
                enable_events=True, 
                key='-FOLDER-OUT-', ),
            sg.FolderBrowse(size=6),
            sg.Button('Save', size=6, key='-SAVE-')
        ]   
    ]

    
    # ----- Full layout -----
    layout = [
        [
            sg.Column(params_column),
            sg.Column(viewer_column),
        ]
    ]
    return layout


def init_canvas_background(window):
    '''Add base background images to output canvas'''
    # https://stackoverflow.com/a/71816897

    back_img_id = window['-CANVAS-'].draw_image(filename='assets/img/background.png', location=(0, 0))
    body_img_id = window['-CANVAS-'].draw_image(filename='assets/img/body_sihl.png', location=canvas_margins)

def upd_pattern_visual(window):

    print('New Pattern!!', pattern_state.png_path)  # DEBUG
    if pattern_state.ui_id is not None:
        window['-CANVAS-'].delete_figure(pattern_state.ui_id)

    # Image body center with the body center of a body silhouette
    # FIXME Still a little too low?
    png_body = pattern_state.body_bottom
    real_b_bottom = np.asarray([429/2 + canvas_margins[0], 530 + canvas_margins[1]])   # Not the very bottom  # TODO relative to resolution
    location = real_b_bottom - png_body

    # TODO Also if too far (e.g. after sleeve removal)
    # TODO Change canvas size to fit a pattern? -> 
    # TODO Bigger background image
    # TODO Higher quality
    # FIXME Body Not deleted =(
    if location[0] < 0: 
        canvas_margins[0] -= location[0]
        window['-CANVAS-'].delete_figure(back_img_id)
        window['-CANVAS-'].delete_figure(body_img_id)
        init_canvas_background(window)
        location[0] = 0

    pattern_state.ui_id = window['-CANVAS-'].draw_image(filename=pattern_state.png_path, location=location.tolist())


def event_loop(window):
    while True:
        event, values = window.read()
        if event == 'Exit' or event == sg.WIN_CLOSED:
            break

        # TODO Parameter update: change corresponding field
        # TODO Any parameter updated: Update MetaGarment and re-load visualization

        # TODO process errors for wrong files chosen
        if event == '-BODY-':
            file = values['-BODY-']
            pattern_state.new_body_file(file)
            upd_pattern_visual(window)
        elif event == '-DESIGN-':  # A file was chosen from the listbox
            file = values['-DESIGN-']
            pattern_state.new_design_file(file)
            upd_pattern_visual(window)
        elif event == '-SAVE-':
            pattern_state.save()
        elif event == '-FOLDER-OUT-':
            pattern_state.save_path = values['-FOLDER-OUT-']

            print('PatternConfigurator::INFO::New output path: ', pattern_state.save_path)


if __name__ == '__main__':

    # Last option needed to finalize GUI initialization and allow modifications
    window = sg.Window('Sewing Pattern Configurator', def_layout((842, 596)), finalize=True)

    init_canvas_background(window)
    upd_pattern_visual(window)

    event_loop(window)

    pattern_state.clear_tmp(root=True)
    window.close()
