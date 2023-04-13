import PySimpleGUI as sg

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

state = State()

def def_layout(canvas_size=(500, 500)):

    # First the window layout in 2 columns

    params_column = [
        [
            sg.Text('Body Mesurements: '),
        ],
        [
            sg.In(
                default_text=state.body_file,
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
                default_text=state.design_file,
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
                default_text=state.save_path, 
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

    window['-CANVAS-'].draw_image(filename='assets/img/background.png', location=(0, 0))
    window['-CANVAS-'].draw_image(filename='assets/img/body_sihl.png', location=(30, 30))

def upd_pattern_visual(window):

    # TODO Proper placement -- align with a body outline
    
    print('New Pattern!!', state.png_path)  # DEBUG
    if state.ui_id is not None:
        window['-CANVAS-'].delete_figure(state.ui_id)
    state.ui_id = window['-CANVAS-'].draw_image(filename=state.png_path, location=(100, 30))


def event_loop(window):
    while True:
        event, values = window.read()
        if event == 'Exit' or event == sg.WIN_CLOSED:
            break

        # TODO Parameter update: change corresponding field
        # TODO Any parameter updated: Update MetaGarment and re-load visualization


        # TODO process errors for wrong files chosen
        # Folder name was filled in, make a list of files in the folder
        if event == '-BODY-':
            file = values['-BODY-']
            state.new_body_file(file)
            upd_pattern_visual(window)
        elif event == '-DESIGN-':  # A file was chosen from the listbox
            file = values['-DESIGN-']
            state.new_design_file(file)
            upd_pattern_visual(window)
        elif event == '-SAVE-':
            state.save()
        elif event == '-FOLDER-OUT-':
            state.save_path = values['-FOLDER-OUT-']

            print('PatternConfigurator::INFO::New output path: ', state.save_path)
            

    window.close()


if __name__ == '__main__':

    # Last option needed to finalize GUI initialization and allow modifications
    window = sg.Window('Sewing Pattern Configurator', def_layout((842, 596)), finalize=True)

    init_canvas_background(window)
    upd_pattern_visual(window)

    event_loop(window)
