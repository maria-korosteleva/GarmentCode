import PySimpleGUI as sg
import os.path

# NOTE: PySimpleGUI reference: https://github.com/PySimpleGUI/PySimpleGUI/blob/master/docs/call%20reference.md

# TODO Instructions
# TODO allow changing window size? https://stackoverflow.com/questions/66379808/how-do-i-respond-to-window-resize-in-pysimplegui
# https://stackoverflow.com/questions/63686020/pysimplegui-how-to-achieve-elements-frames-columns-to-align-to-the-right-and-r

save_path = os.path.abspath("./")

def def_layout(canvas_size=(500, 500)):

    # First the window layout in 2 columns

    params_column = [
        [
            sg.Text("Image Folder"),
            sg.In(size=(25, 1), enable_events=True, key="-FOLDER-"),
            sg.FolderBrowse(),
        ],
        [
            sg.Listbox(
                values=[], enable_events=True, size=(40, 20), key="-FILE LIST-"
            )
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
            sg.Text("Output Folder:"),
            sg.In(
                default_text=save_path, 
                expand_x=True, 
                enable_events=True, 
                key="-FOLDER-OUT-", ),
            sg.FolderBrowse(size=6),
            sg.Button('Save', size=6)
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
    """Add base background images to output canvas"""
    # https://stackoverflow.com/a/71816897

    window['-CANVAS-'].draw_image(filename='gui/background.png', location=(0, 0))
    window['-CANVAS-'].draw_image(filename='gui/sihl.png', location=(30, 30))



def event_loop(window):
    while True:
        event, values = window.read()
        if event == "Exit" or event == sg.WIN_CLOSED:
            break

        # Folder name was filled in, make a list of files in the folder
        if event == "-FOLDER-":
            folder = values["-FOLDER-"]
            try:
                # Get list of files in folder
                file_list = os.listdir(folder)
            except:
                file_list = []

            fnames = [
                f
                for f in file_list
                if os.path.isfile(os.path.join(folder, f))
                and f.lower().endswith((".png", ".gif"))
            ]
            window["-FILE LIST-"].update(fnames)
        elif event == "-FILE LIST-":  # A file was chosen from the listbox
            try:
                filename = os.path.join(
                    values["-FOLDER-"], values["-FILE LIST-"][0]
                )
                window["-TOUT-"].update(filename)
                window["-IMAGE-"].update(filename=filename)
            except:
                pass
        elif event == "-FOLDER-OUT-":
            save_path = values["-FOLDER-OUT-"]

            print('PatternConfigurator::INFO::New output path: ', save_path)
            

    window.close()


if __name__ == "__main__":

    # Last option needed to finalize GUI initialization and allow modifications
    window = sg.Window("Image Viewer", def_layout((842, 596)), finalize=True)

    init_canvas_background(window)

    event_loop(window)
