"""Callback functions & State info for Sewing Pattern Configurator """

# NOTE: PySimpleGUI reference: https://github.com/PySimpleGUI/PySimpleGUI/blob/master/docs/call%20reference.md

# TODO allow changing window size? https://stackoverflow.com/questions/66379808/how-do-i-respond-to-window-resize-in-pysimplegui
# https://stackoverflow.com/questions/63686020/pysimplegui-how-to-achieve-elements-frames-columns-to-align-to-the-right-and-r
# TODO Visual appearance
# https://github.com/PySimpleGUI/PySimpleGUI/issues/3412 for nice buttons & stuff
# Native demo https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Simple_Material_Feel.py
# TODO Icons

import os.path
from pathlib import Path
from datetime import datetime
import yaml
import shutil 
import numpy as np
import PySimpleGUI as sg


# Custom 
from assets.garment_programs.meta_garment import MetaGarment

class GUIState():
    """State of GUI-related objects"""
    def __init__(self) -> None:
        self.window = None

        # Pattern
        self.pattern_state = GUIPattern()

        # Pattern display
        self.default_canvas_margins = [20, 20]
        self.canvas_margins = self.default_canvas_margins
        self.body_img_id = None
        self.back_img_id = None

        # Last option needed to finalize GUI initialization and allow modifications
        self.window = sg.Window(
            'Sewing Pattern Configurator', 
            self.def_layout((842, 596)), 
            finalize=True)
        self.init_canvas_background()
        self.upd_pattern_visual()


    def __del__(self):
        """Clenup"""
        self.pattern_state.clear_tmp(root=True)
        self.window.close()


    def def_layout(self, canvas_size=(500, 500)):

        # First the window layout in 2 columns

        params_column = [
            [
                sg.Text('Body Mesurements: '),
            ],
            [
                sg.In(
                    default_text=self.pattern_state.body_file,
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
                    default_text=self.pattern_state.design_file,
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
                    default_text=self.pattern_state.save_path, 
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

    def init_canvas_background(self):
        '''Add base background images to output canvas'''
        # https://stackoverflow.com/a/71816897

        self.back_img_id = self.window['-CANVAS-'].draw_image(
            filename='assets/img/background.png', location=(0, 0))
        self.body_img_id = self.window['-CANVAS-'].draw_image(
            filename='assets/img/body_sihl.png', location=self.canvas_margins)

    def upd_pattern_visual(self):

        print('New Pattern!!', self.pattern_state.png_path)  # DEBUG
        if self.pattern_state.ui_id is not None:
            self.window['-CANVAS-'].delete_figure(self.pattern_state.ui_id)

        # Image body center with the body center of a body silhouette
        # FIXME Still a little too low?
        png_body = self.pattern_state.body_bottom
        real_b_bottom = np.asarray([429/2 + self.canvas_margins[0], 530 + self.canvas_margins[1]])   # Not the very bottom  # TODO relative to resolution
        location = real_b_bottom - png_body

        # TODO Also if too far (e.g. after sleeve removal)
        # TODO Change canvas size to fit a pattern? -> 
        # TODO Bigger background image
        # TODO Higher quality
        if location[0] < 0: 
            self.canvas_margins[0] -= location[0]
            self.window['-CANVAS-'].delete_figure(self.back_img_id)
            self.window['-CANVAS-'].delete_figure(self.body_img_id)
            self.init_canvas_background()
            location[0] = 0

        self.pattern_state.ui_id = self.window['-CANVAS-'].draw_image(
            filename=self.pattern_state.png_path, location=location.tolist())

    def event_loop(self):
        while True:
            event, values = self.window.read()
            if event == 'Exit' or event == sg.WIN_CLOSED:
                break

            # TODO Parameter update: change corresponding field
            # TODO Any parameter updated: Update MetaGarment and re-load visualization

            # TODO process errors for wrong files chosen
            if event == '-BODY-':
                file = values['-BODY-']
                self.pattern_state.new_body_file(file)
                self.upd_pattern_visual()
            elif event == '-DESIGN-':  # A file was chosen from the listbox
                file = values['-DESIGN-']
                self.pattern_state.new_design_file(file)
                self.upd_pattern_visual()
            elif event == '-SAVE-':
                self.pattern_state.save()
            elif event == '-FOLDER-OUT-':
                self.pattern_state.save_path = values['-FOLDER-OUT-']

                print('PatternConfigurator::INFO::New output path: ', self.pattern_state.save_path)


class GUIPattern():
    def __init__(self) -> None:
        self.save_path = os.path.abspath('./')   # TODO Use Path()
        self.png_path = None
        self.tmp_path = os.path.abspath('./tmp')
        # create tmp path
        Path(self.tmp_path).mkdir(parents=True, exist_ok=True)

        self.ui_id = None   # ID of current object in the interface
        self.body_bottom = None   # Location of body center in the current png representation of a garment

        self.body_file = None
        self.design_file = None
        self.new_body_file(
            os.path.abspath('./assets/body_measurments/f_smpl_avg.yaml')
        )
        self.new_design_file(
            os.path.abspath('./assets/design_params/base.yaml')
        )

    # Info
    def isReady(self):
        """Check if the State is correct to load and save garments"""
        return self.body_file is not None and self.design_file is not None

    # Updates
    def new_body_file(self, path):
        self.body_file = path
        with open(path, 'r') as f:
            body = yaml.safe_load(f)['body']
            body['waist_level'] = body['height'] - body['head_l'] - body['waist_line']
        self.body_params = body
        self.reload_garment()

    def new_design_file(self, path):
        self.design_file = path
        with open(path, 'r') as f:
            des = yaml.safe_load(f)['design']
        self.design_params = des
        self.reload_garment()

    def reload_garment(self):
        """Reload sewing pattern with current body and design parameters"""
        if self.isReady():
            self.sew_pattern = MetaGarment('Configured_design', self.body_params, self.design_params)
            self._view_serialize()

    def _view_serialize(self):
        """Save a sewing pattern svg/png representation to tmp folder be used for display"""

        # Clear up the folder from previous version -- it's not needed any more
        self.clear_tmp()
        pattern = self.sew_pattern()
        # Save as json file
        folder = pattern.serialize(
            self.tmp_path, 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=True, 
            with_3d=False, with_text=False, view_ids=False)
        
        self.body_bottom = np.asarray(pattern.body_bottom_shift)

        # get PNG file!
        root, _, files = next(os.walk(folder))
        for filename in files:
            if 'pattern.png' in filename and '3d' not in filename:
                self.png_path = os.path.join(root, filename)
                break

    def clear_tmp(self, root=False):
        """Clear tmp folder"""
        shutil.rmtree(self.tmp_path)
        if not root:
            Path(self.tmp_path).mkdir(parents=True, exist_ok=True)

    # Current state
    def save(self):
        """Save current garment design to self.save_path """

        pattern = self.sew_pattern()

        # Save as json file
        folder = pattern.serialize(
            self.save_path, 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=True, 
            with_3d=True, with_text=False, view_ids=False)

        shutil.copy(self.body_file, folder)  # TODO Better name!
        shutil.copy(self.design_file, folder)

        print(f'Success! {self.sew_pattern.name} saved to {folder}')
