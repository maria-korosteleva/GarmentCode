"""Callback functions & State info for Sewing Pattern Configurator """

# NOTE: PySimpleGUI reference: https://github.com/PySimpleGUI/PySimpleGUI/blob/master/docs/call%20reference.md

# TODOLOW LOW-Priority allow changing window size? https://stackoverflow.com/questions/66379808/how-do-i-respond-to-window-resize-in-pysimplegui
# https://stackoverflow.com/questions/63686020/pysimplegui-how-to-achieve-elements-frames-columns-to-align-to-the-right-and-r
# TODOLOW Low-Priority Colorscheme
# TODO Window is too big on Win laptops

import os.path
from copy import copy, deepcopy
from pathlib import Path
from datetime import datetime
import yaml
import shutil 
import numpy as np
import PySimpleGUI as sg


# Custom 
from assets.garment_programs.meta_garment import MetaGarment
from assets.body_measurments.body_params import BodyParameters
import pypattern as pyp

verbose = False

# GUI Elements
def Collapsible(layout, key, title='', arrows=(sg.SYMBOL_DOWN, sg.SYMBOL_RIGHT), collapsed=True):
    """
    User Defined Element
    A "collapsable section" element. Like a container element that can be collapsed and brought back
    :param layout:Tuple[List[sg.Element]]: The layout for the section
    :param key:Any: Key used to make this section visible / invisible
    :param title:str: Title to show next to arrow
    :param arrows:Tuple[str, str]: The strings to use to show the section is (Open, Closed).
    :param collapsed:bool: If True, then the section begins in a collapsed state
    :return:sg.Column: Column including the arrows, title and the layout that is pinned

    # NOTE: from https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Column_Collapsible_Sections.py

    """
    return sg.Column([[sg.T((arrows[1] if collapsed else arrows[0]), enable_events=True, k=key+'#BUTTON'),
                       sg.T(title, enable_events=True, key=key+'#TITLE')],
                      [sg.pin(sg.Column(layout, key=key, visible=not collapsed, metadata=arrows))]], pad=(0,0))

icon_image_b64 = b'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'

# State of GUI
# TODO Add randomization
class GUIPattern():
    def __init__(self) -> None:
        self.save_path = Path.cwd() / 'Logs' 
        self.png_path = None
        self.tmp_path = Path.cwd() / 'tmp'
        
        # create paths
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.tmp_path.mkdir(parents=True, exist_ok=True)

        self.ui_id = None   # ID of current object in the interface
        self.body_bottom = None   # Location of body center in the current png representation of a garment

        self.design_sampler = pyp.params.DesignSampler()

        self.body_file = None
        self.design_file = None
        self.design_params = {}
        self.new_body_file(
            Path.cwd() / 'assets/body_measurments/f_smpl_avg.yaml'
        )
        self.new_design_file(
            Path.cwd() / 'assets/design_params/default.yaml'
        )

    # Info
    def isReady(self):
        """Check if the State is correct to load and save garments"""
        return self.body_file is not None and self.design_file is not None

    # Updates
    def new_body_file(self, path):
        self.body_file = path
        self.body_params = BodyParameters(path)
        self.reload_garment()

    def new_design_file(self, path):
        self.design_file = path

        # Update values
        with open(path, 'r') as f:
            des = yaml.safe_load(f)['design']
        # FIXME Updating should allows loading partial design files
        # Need nested updates
        self.design_params.update(des)

        if 'left' in self.design_params and not self.design_params['left']['enable_asym']:
            self.sync_left()

        # Update param sampler
        self.design_sampler.load(path)

        # Reload
        self.reload_garment()

    def set_design_param(self, param_path, new_value, reload=True):
        """Set the new value of design params"""

        dic = self.design_params
        param = param_path[-1]

        # Skip the top levels
        # https://stackoverflow.com/a/37704379
        for key in param_path[:-1]:
            dic = dic.setdefault(key, {})
        
        # Ensure correct typization
        if dic[param]['type'] == 'int':
            new_value = int(new_value)
        elif dic[param]['type'] == 'bool':
            new_value = bool(new_value)
        elif dic[param]['type'] == 'float':
            new_value = float(new_value)
        # Otherwise stays as is
        dic[param]['v'] = new_value

        if 'enable_asym' in param_path and new_value == False:
            self.sync_left()

        if ('left' not in param_path 
                and 'meta' not in param_path 
                and not self.design_params['left']['enable_asym']['v']
                and param_path[0] in self.design_params['left']):
            # Copy the fields to the left side
            dic = self.design_params['left']
            # Skip the top levels
            # https://stackoverflow.com/a/37704379
            for key in param_path[:-1]:
                dic = dic.setdefault(key, {})

            dic[param]['v'] = new_value

        if reload:
            self.reload_garment()

    def sample_design(self):
        """Random design parameters"""

        while True:
            new_design = self.design_sampler.randomize()
            self.design_params.update(new_design)
            self.reload_garment()

            if self.sew_pattern.is_self_intersecting():
                # Let the user know
                out = sg.popup_yes_no(
                    'The design is self-intersecting. Generate a new one?', 
                    title='Self-Intersecting',
                    icon=icon_image_b64)

                if out == 'No':
                    break
            else:
                break

    def restore_design(self):
        """Restore design values to match the current loaded file"""
        new_design = self.design_sampler.default()
        self.design_params.update(new_design)
        self.reload_garment()

    def reload_garment(self):
        """Reload sewing pattern with current body and design parameters"""
        if self.isReady():
            self.sew_pattern = MetaGarment('Configured_design', self.body_params, self.design_params)
            self._view_serialize()

    def sync_left(self):
        # Syncronize left and right
        for k in self.design_params['left']:
            if k != 'enable_asym':
                self.design_params['left'][k] = deepcopy(self.design_params[k])

    def _view_serialize(self):
        """Save a sewing pattern svg/png representation to tmp folder be used for display"""

        # Clear up the folder from previous version -- it's not needed any more
        self.clear_tmp()
        pattern = self.sew_pattern()

        if not len(pattern.panel_order()): 
            # Empty pattern
            self.png_path = ''
            return

        # Save as json file
        folder = pattern.serialize(
            self.tmp_path, 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=True, 
            with_3d=False, with_text=False, view_ids=False)
        
        self.body_bottom = np.asarray(pattern.body_bottom_shift)
        self.png_size = pattern.png_size

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
            self.tmp_path.mkdir(parents=True, exist_ok=True)

    # Current state
    def save(self):
        """Save current garment design to self.save_path """

        pattern = self.sew_pattern()

        # Save as json file
        folder = pattern.serialize(
            self.save_path, 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=True, 
            with_3d=True, with_text=False, view_ids=False, 
            empty_ok=True)

        self.body_params.save(folder)

        with open(Path(folder) / 'design_params.yaml', 'w') as f:
            yaml.dump(
                {'design': self.design_params}, 
                f,
                default_flow_style=False,
                sort_keys=False
            )

        print(f'Success! {self.sew_pattern.name} saved to {folder}')

# FIXME Direct editing of file fields should not result in crashes (= don't send event at each edit)
class GUIState():
    """State of GUI-related objects
    
        NOTE: "#" is used as a separator in GUI keys to avoid confusion with
            symbols that can be (typically) used in body/design parameter names 
            ('_', '-', etc.) 

    """
    def __init__(self) -> None:
        self.window = None

        # Pattern
        self.pattern_state = GUIPattern()

        # Pattern display
        self.min_margin = 10
        self.default_body_img_margins = [125, 20] 
        self.body_img_margins = copy(self.default_body_img_margins)
        self.body_img_id = None
        self.back_img_id = None
        self.def_canvas_size = (1315, 670)   # 
        self.body_img_size = (None, None)  # NOTE updated in subroutines

        # Last option needed to finalize GUI initialization and allow modifications
        self.theme()
        self.window = sg.Window(
            'Sewing Pattern Configurator', 
            self.def_layout(self.pattern_state, self.def_canvas_size), 
            icon=icon_image_b64,
            finalize=True)
        
        # Modifiers after window finalization
        self.input_text_on_enter('BODY#')
        self.input_text_on_enter('DESIGN#')
        self.prettify_sliders()
        self.init_canvas_background()
        self.init_body_silhouette()

        # Draw initial pattern
        self.upd_pattern_visual()

    def __del__(self):
        """Clenup"""
        self.pattern_state.clear_tmp(root=True)
        self.window.close()

    # Pretty stuff
    def theme(self):
        """Define and apply custom theme"""
        # Native demo https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Simple_Material_Feel.py
        # https://stackoverflow.com/a/74625488

        gui_theme = {
            "BACKGROUND": sg.COLOR_SYSTEM_DEFAULT,  #'#FFF9E7', 
            "TEXT": sg.COLOR_SYSTEM_DEFAULT, 
            "INPUT": sg.COLOR_SYSTEM_DEFAULT,
            "TEXT_INPUT": sg.COLOR_SYSTEM_DEFAULT, 
            "SCROLL": sg.COLOR_SYSTEM_DEFAULT,
            "BUTTON":  ('#505050', '#CECECE'),  # sg.COLOR_SYSTEM_DEFAULT, # ('#A714FF', '#F6E7FF'),  # sg.OFFICIAL_PYSIMPLEGUI_BUTTON_COLOR, 
            "PROGRESS": sg.COLOR_SYSTEM_DEFAULT, 
            "BORDER": 0,
            "SLIDER_DEPTH": 0.5, 
            "PROGRESS_DEPTH": 0
        }

        sg.theme_add_new('SewPatternsTheme', gui_theme)
        sg.theme('SewPatternsTheme')

    # Layout initialization / updates
    def def_layout(self, pattern, canvas_size=(500, 500)):

        # First the window layout in 2 columns

        body_layout = self.def_body_layout(pattern)

        design_layout = [
            [
                sg.Text('Design parameters: '),
            ],
            [
                sg.In(
                    default_text=self.pattern_state.design_file,
                    size=(25, 1), 
                    enable_events=True, 
                    key='DESIGNFILE'
                ),
                sg.FileBrowse(initial_folder=self.pattern_state.design_file.parent)
            ],
            [
                sg.Button(   # TODO Add some color
                    'Randomize',
                    enable_events=True, 
                    key='DESIGNRANDOMIZE'
                ),
                sg.Button(   # TODO Add some color
                    'Restore Default',
                    enable_events=True, 
                    key='DESIGNRESTORE'
                )
            ],
            [
                sg.Column(self.def_design_tabs())
            ]
            
        ]

        # For now will only show the name of the file that was chosen
        viewer_column = [
            [
                sg.Text(
                    '', 
                    text_color='red', 
                    key='TEXT-SELF-INTERSECTION'),
                sg.Push(),
                sg.Checkbox(
                    'Display Reference Silhouette', 
                    default=True,
                    key='BODYDISPLAY',
                    enable_events=True
                )
            ],
            [
                sg.Graph(
                    canvas_size=canvas_size, 
                    graph_bottom_left=(0, canvas_size[1]), 
                    graph_top_right=(canvas_size[0], 0), 
                    background_color='white', 
                    key='CANVAS')
            ],      
            [
                sg.Text('Output Folder:'),
                sg.In(
                    default_text=self.pattern_state.save_path, 
                    expand_x=True, 
                    enable_events=True, 
                    key='FOLDER-OUT', ),
                sg.FolderBrowse(initial_folder=self.pattern_state.save_path),
                sg.Button('Save', size=6, key='SAVE')
            ]   
        ]

        
        # ----- Full layout -----
        layout = [
            [
                sg.TabGroup(
                    [[
                        sg.Tab('Design', design_layout), 
                        sg.Tab('Body', body_layout)
                    ]], 
                    expand_y=True, 
                    tab_border_width=0, 
                    border_width=0,
                    size=(550, 1150)    # 1100
                ),
                sg.Column(viewer_column),
            ]
        ]
        return layout

    def def_body_layout(self, guipattern:GUIPattern):
        """Add fields to control body measurements"""

        param_input_col = []

        body = guipattern.body_params
        for param in body:
            param_input_col.append([
                sg.Text(
                    param.strip('_') + ':', 
                    justification='right', 
                    expand_x=True), 

                sg.Input(
                    str(body[param]), 
                    enable_events=False,  # Events enabled outside: only on Enter 
                    key=f'BODY#{param}', 
                    size=7,
                    disabled=True if param[0] == '_' else False) 
                ])
            
        layout = [
            [
                sg.Text('Body Mesurements: '),
            ],
            [
                sg.In(
                    default_text=self.pattern_state.body_file,
                    size=(25, 1), 
                    enable_events=True,  
                    key='BODYFILE'
                ),
                sg.FileBrowse(initial_folder=self.pattern_state.body_file.parent)
            ],
            [
                sg.Column(param_input_col)
            ]
        ]

        return layout

    def def_flat_design_layout(self, design_params, pre_key='DESIGN', use_collapsible=False):
        """Add fields to control design parameters"""

        # TODOLOW Unused/non-relevant fields  

        text_size = max([len(param) for param in design_params])

        fields = []
        for param in design_params:
            if '#' in param:
                raise ValueError(f'GUI::ERROR::parameter name {param} contains special symbol #. Please, rename the paramer to avoing this symbol')
            if 'v' in design_params[param]:

                p_type = design_params[param]['type']

                if 'select' in p_type:
                    values = design_params[param]['range']
                    if 'null' in p_type and not None in values:
                        values.append(None)
                    in_field = sg.Combo(
                        values=design_params[param]['range'], 
                        default_value=design_params[param]['v'],
                        enable_events=True,
                        key=f'{pre_key}#{param}',
                    )
                elif p_type == 'bool':
                    in_field = sg.Checkbox(
                        param, 
                        default=design_params[param]['v'], 
                        key=f'{pre_key}#{param}',
                        enable_events=True, 
                        expand_x=True)
                elif p_type == 'int' or p_type == 'float':
                    in_field = sg.Slider( 
                        design_params[param]['range'], 
                        default_value=design_params[param]['v'],  
                        orientation='horizontal',
                        relief=sg.RELIEF_FLAT, 
                        resolution=1 if p_type == 'int' else 0.05, 
                        key=f'{pre_key}#{param}', 
                        # DRAFT enable_events=True # comment to only send events when slider is released
                    )
                elif 'file' in p_type:
                    default_path = Path(design_params[param]['v'])
                    ftype = p_type.split('_')[-1]
                    in_field = sg.Column(
                        [
                            [
                                sg.In(
                                    default_text=default_path,
                                    size=(15, 1), 
                                    enable_events=True, 
                                    key=f'{pre_key}#{param}',
                                    readonly=True  # FIXME this is a patch to avoid crashes when the field is edited directly
                                ),
                                sg.FileBrowse(
                                    initial_folder=default_path.parent,
                                    file_types=((f'{ftype.upper()} Files', f'*.{ftype}'),)
                                )
                            ]
                        ]
                    )
                else:
                    print(f'GUI::WARNING::Unknown parameter type: {p_type}')
                    in_field = sg.Input(
                        str(design_params[param]['v']), 
                        enable_events=False,  # Events enabled outside: only on Enter 
                        key=f'{pre_key}#{param}', 
                        size=7) 

                fields.append(
                    [
                        sg.Text(
                            param + ':', 
                            justification='right', 
                            size=text_size + 1
                        ), 
                        in_field
                    ])
                
                
            else:  # subsets of params
                if use_collapsible:
                    fields.append(
                        [ 
                            Collapsible(
                                self.def_flat_design_layout(
                                    design_params[param], 
                                    pre_key=f'{pre_key}#{param}'
                                ), 
                                title=param,
                                key=f'COLLAPSE-{pre_key}#{param}'
                            )
                        ])
                else:
                    fields.append(
                        [ 
                            sg.Frame(
                                param,
                                self.def_flat_design_layout(
                                    design_params[param], 
                                    pre_key=f'{pre_key}#{param}'
                                ), 
                                key=f'COLLAPSE-{pre_key}#{param}',
                                expand_x=True
                            )
                        ])
        
        return fields

    def def_design_tabs(self, pre_key='DESIGN'):
        """Top level categories into tabs"""

        design_params = self.pattern_state.design_params
        tabs = []
        for param in design_params:
            if '#' in param:
                raise ValueError(f'GUI::ERROR::parameter name {param} contains special symbol #. Please, rename the paramer to avoing this symbol')
  
            if 'v' in design_params[param]:
                sg.popup_error_with_traceback(
                    f'Leaf parameter on top level of design hierarchy: {param}!!'
                )
                continue
            # Tab
            tabs.append(
                sg.Tab(
                    param, 
                    self.def_flat_design_layout(
                        design_params[param], 
                        pre_key=f'{pre_key}#{param}', 
                        use_collapsible=(param == 'left')
                    ))
            )

        return [[sg.TabGroup(
                    [tabs], 
                    tab_location='lefttop', 
                    tab_border_width=0, 
                    border_width=0
                )]]

    def init_canvas_background(self):
        '''Add base background image to output canvas'''
        # https://stackoverflow.com/a/71816897

        if self.back_img_id is not None:
            self.window['CANVAS'].delete_figure(self.back_img_id)
        
        self.back_img_id = self.window['CANVAS'].draw_image(
            filename='assets/img/millimiter_paper_1500_900.png', location=(0, 0))

    def init_body_silhouette(self):
        """Add body figure to canvas"""
        if self.body_img_id is not None:
            self.window['CANVAS'].delete_figure(self.body_img_id)
        self.body_img_id = self.window['CANVAS'].draw_image(
            filename='assets/img/body_30_opacity.png', location=self.body_img_margins)
        
        bbox = self.window['CANVAS'].get_bounding_box(self.body_img_id)
        self.body_img_size = (
            abs(bbox[0][0] - bbox[1][0]), 
            abs(bbox[0][1] - bbox[1][1]), 
        )  

    # Updates
    def upd_canvas_size(self, new):
        """Update size of canvas (visualization window)
        
            NOTE: Nothing is updated if the size is the same
        """

        # https://github.com/PySimpleGUI/PySimpleGUI/issues/2842#issuecomment-890049683
        upd_canvas_size = (
            max(new[0], self.def_canvas_size[0]),
            max(new[1], self.def_canvas_size[1])
        )
        if upd_canvas_size == self.window['CANVAS'].get_size():
            # Don't do anything if the size didn't actually change
            return
        
        if verbose:
            print(f'GUI::Info::Resizing::{upd_canvas_size} from {self.window["CANVAS"].get_size()}')

        # UPD canvas
        self.window['CANVAS'].set_size(upd_canvas_size)
        self.window['CANVAS'].change_coordinates(
            (0, upd_canvas_size[1]), (upd_canvas_size[0], 0))

    def upd_pattern_visual(self):

        if self.pattern_state.ui_id is not None:
            self.window['CANVAS'].delete_figure(self.pattern_state.ui_id)
            self.pattern_state.ui_id = None

        if not self.pattern_state.png_path:  # Empty pattern
            return

        # Image body center with the body center of a body silhouette
        png_body = self.pattern_state.body_bottom
        real_b_bottom = np.asarray([
            self.body_img_size[0]/2 + self.default_body_img_margins[0], 
            self.body_img_size[1]*0.95 + self.default_body_img_margins[1]
        ])  # Coefficient to account for feet projection -- the bottom is lower then floor level
        location = real_b_bottom - png_body

        # Adjust the body location (margins) to fit the pattern
        if location[0] < 0: 
            self.body_img_margins[0] = self.default_body_img_margins[0] - location[0]
            self.body_img_margins[1] = self.default_body_img_margins[1]
            location[0] = 0
        else: 
            self.body_img_margins[:] = self.default_body_img_margins
        
        # Change canvas size to fit a pattern (if needed)
        self.upd_canvas_size((
            location[0] + self.pattern_state.png_size[0] + self.min_margin,
            location[1] + self.pattern_state.png_size[1] + self.min_margin
        ))
        # Align body with the pattern
        if self.body_img_id is not None:
            self.window['CANVAS'].relocate_figure(self.body_img_id, *self.body_img_margins)

        # Display the pattern
        self.pattern_state.ui_id = self.window['CANVAS'].draw_image(
            filename=self.pattern_state.png_path, location=location.tolist())

    def upd_fields_body(self):
        """Update current values of the fields 
            if they were loaded from a file
        """
        fields = self.get_keys_by_instance_tag(sg.Input, 'BODY#')
        for elem in fields:
            param = elem.split('#')[1]
            self.window[elem].update(self.pattern_state.body_params[param])
    
    def upd_fields_design(self, design_params, pre_key='DESIGN'):
        """Update current values of the fields 
            if they were loaded from a file
        """
        for param in design_params:
            # skip unknown parameters
            
            if 'v' in design_params[param]:
                if f'{pre_key}#{param}' in self.window.AllKeysDict:
                    val = design_params[param]['v']
                    self.window[f'{pre_key}#{param}'].update(val if val is not None else 'None')
                elif verbose:
                    print(f'Info::{pre_key}#{param}: unknown element. Skipped')
            else:
                self.upd_fields_design(
                    design_params[param], 
                    f'{pre_key}#{param}'
                )

    def upd_self_intersecting(self):
        """Indicate if the current pattern is self-intersecting"""
        if self.pattern_state.sew_pattern.is_self_intersecting():
            self.window['TEXT-SELF-INTERSECTION'].update(
                'WARNING: Some of the panels are self-intersecting')
        else:
            self.window['TEXT-SELF-INTERSECTION'].update('')

    # Modifiers after window finalization
    def input_text_on_enter(self, tag):
        """Modify input text elements to only send events when Enter is pressed"""
        # https://stackoverflow.com/a/68528658

        # All body updates
        fields = self.get_keys_by_instance_tag(sg.Input, tag)
        for key in fields:
            self.window[key].bind('<Return>', '#ENTER')

    def prettify_sliders(self):
        """ Make slider knowbs flat and small
            A bit of hack accessing lower level library (Tkinter) to reach the needed setting
            NOTE: It needs to be executed after window finalization
        """
        # https://github.com/PySimpleGUI/PySimpleGUI/issues/10#issuecomment-997426666
        # https://www.tutorialspoint.com/python/tk_scale.htm
        # https://tkdocs.com/pyref/scale.html
        window = self.window
        slider_keys = self.get_keys_by_instance(sg.Slider)
        for key in slider_keys:
            window[key].Widget.config(sliderlength=10)
            window[key].Widget.config(sliderrelief=sg.RELIEF_FLAT)
            window[key].bind('<ButtonRelease-1>', '')  # DRAFT  uncomment to only send events when slider is released
            # window[key].Widget.config(background='#000000') # slider button
            # window[key].Widget.config(troughcolor='#FFFFFF')  

    # Utils
    def get_keys_by_instance(self, instance_type):
        # https://github.com/PySimpleGUI/PySimpleGUI/issues/10#issuecomment-997426666
        return [key for key, value in self.window.key_dict.items() if isinstance(value, instance_type)]

    def get_keys_by_instance_tag(self, instance_type, tag):
        # https://github.com/PySimpleGUI/PySimpleGUI/issues/10#issuecomment-997426666
        return [key for key, value in self.window.key_dict.items() if isinstance(value, instance_type) and tag in key]

    # Main loop
    def event_loop(self):
        while True:
            event, values = self.window.read()

            # --- Window layout actions ---
            if event == 'Exit' or event == sg.WIN_CLOSED:
                break
            elif event.startswith('COLLAPSE'):
                field = event.removesuffix('#BUTTON').removesuffix('#TITLE')
                # Visibility
                self.window[field].update(visible=not self.window[field].visible)
                # UPD graphic
                self.window[field + '#BUTTON'].update(
                    self.window[field].metadata[0] if self.window[field].visible else self.window[field].metadata[1])
            elif event == 'BODYDISPLAY':
                # Toggle display of body figure
                if self.body_img_id is not None:
                    # Already diplayed
                    self.window['CANVAS'].delete_figure(self.body_img_id)
                    self.body_img_id = None
                else:
                    self.init_body_silhouette()
                    # rearrange images correctly 
                    self.window['CANVAS'].send_figure_to_back(self.body_img_id)
                    self.window['CANVAS'].send_figure_to_back(self.back_img_id)

            # ----- Garment-related actions -----
            try: 
                if event == 'BODYFILE':
                    file = values['BODYFILE']
                    self.pattern_state.new_body_file(file)

                    self.upd_fields_body()
                    self.upd_pattern_visual()

                elif event.startswith('BODY#') and '#ENTER' in event:
                    # Updated body parameter:
                    param = event.split('#')[1]
                    new_value = values[event.removesuffix('#ENTER')]

                    try:   # https://stackoverflow.com/a/67432444
                        self.pattern_state.body_params[param] = float(new_value)
                    except: # check numerical
                        sg.popup(
                            'Only numerical values are supported (int, float)',
                            icon=icon_image_b64
                        )
                    else:
                        self.pattern_state.reload_garment()
                        self.upd_fields_body()
                        self.upd_pattern_visual()

                elif event.startswith('DESIGN#'): 
                    # Updated body parameter:
                    event_name = event.removesuffix('#ENTER')
                    param_ids = event_name.split('#')[1:]
                    new_value = values[event_name]
                    if verbose:
                        print(f'GUI::Info::New Design Event: {event} = {new_value} of {type(new_value)}')

                    self.pattern_state.set_design_param(
                        param_ids, new_value)
                    self.upd_fields_design(self.pattern_state.design_params)
                    self.upd_pattern_visual()


                elif event == 'DESIGNFILE':  # A file was chosen from the listbox
                    file = values['DESIGNFILE']
                    self.pattern_state.new_design_file(file)

                    self.upd_fields_design(self.pattern_state.design_params)
                    self.upd_pattern_visual()
                
                elif event == 'DESIGNRANDOMIZE':  # A file was chosen from the listbox
                    self.pattern_state.sample_design()

                    self.upd_fields_design(self.pattern_state.design_params)
                    self.upd_pattern_visual()
                
                elif event == 'DESIGNRESTORE':  # A file was chosen from the listbox
                    self.pattern_state.restore_design()

                    self.upd_fields_design(self.pattern_state.design_params)
                    self.upd_pattern_visual()

                elif event == 'SAVE':
                    self.pattern_state.save()

                elif event == 'FOLDER-OUT':
                    self.pattern_state.save_path = Path(values['FOLDER-OUT'])

                    if verbose:
                        print(
                            'PatternConfigurator::INFO::New output path: ', 
                            self.pattern_state.save_path)
                        
                # Check self-intersection
                self.upd_self_intersecting()
            
            except BaseException as e:
                sg.popup_error_with_traceback(
                    'Application ERROR detected (see below)', 
                    str(e),
                    '',
                    'Most likely, the generated pattern is in incorrect state due to current parameter values',
                    '   Undo your last change to return to correct garment state and click "Close"',
                    ''
                )

