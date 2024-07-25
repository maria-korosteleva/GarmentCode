"""Callback functions & State info for Sewing Pattern Configurator """

# NOTE: NiceGUI reference: https://nicegui.io/

import yaml
import traceback
from datetime import datetime
from argparse import Namespace
import numpy as np
import shutil
from pathlib import Path

from nicegui import ui, app, events

# Async execution of regular functions
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Custom
from .gui_pattern import GUIPattern


icon_github = """
    <svg viewbox="0 0 98 96" xmlns="http://www.w3.org/2000/svg">
    <path fill-rule="evenodd" clip-rule="evenodd" d="M48.854 0C21.839 0 0 22 0 49.217c0 
    21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 
    0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 
    4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 
    0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 
    12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 
    13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.304.89 
    2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691C97.707 22 75.788 0 48.854 0z" fill="#fff"/>
    </svg>
    """
icon_arxiv = """<svg id="primary_logo_-_single_color_-_white" data-name="primary logo - single color - white" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 246.978 110.119"><path d="M492.976,269.5l24.36-29.89c1.492-1.989,2.2-3.03,1.492-4.723a5.142,5.142,0,0,0-4.481-3.161h0a4.024,4.024,0,0,0-3.008,1.108L485.2,261.094Z" transform="translate(-358.165 -223.27)" fill="#fff"/><path d="M526.273,325.341,493.91,287.058l-.972,1.033-7.789-9.214-7.743-9.357-4.695,5.076a4.769,4.769,0,0,0,.015,6.53L520.512,332.2a3.913,3.913,0,0,0,3.137,1.192,4.394,4.394,0,0,0,4.027-2.818C528.4,328.844,527.6,327.133,526.273,325.341Z" transform="translate(-358.165 -223.27)" fill="#fff"/><path d="M479.215,288.087l6.052,6.485L458.714,322.7a2.98,2.98,0,0,1-2.275,1.194,3.449,3.449,0,0,1-3.241-2.144c-.513-1.231.166-3.15,1.122-4.168l.023-.024.021-.026,24.851-29.448m-.047-1.882-25.76,30.524c-1.286,1.372-2.084,3.777-1.365,5.5a4.705,4.705,0,0,0,4.4,2.914,4.191,4.191,0,0,0,3.161-1.563l27.382-29.007-7.814-8.372Z" transform="translate(-358.165 -223.27)" fill="#fff"/><path d="M427.571,255.154c1.859,0,3.1,1.24,3.985,3.453,1.062-2.213,2.568-3.453,4.694-3.453h14.878a4.062,4.062,0,0,1,4.074,4.074v7.828c0,2.656-1.327,4.074-4.074,4.074-2.656,0-4.074-1.418-4.074-4.074V263.3H436.515a2.411,2.411,0,0,0-2.656,2.745v27.188h10.007c2.658,0,4.074,1.329,4.074,4.074s-1.416,4.074-4.074,4.074h-26.39c-2.659,0-3.986-1.328-3.986-4.074s1.327-4.074,3.986-4.074h8.236V263.3h-7.263c-2.656,0-3.985-1.329-3.985-4.074,0-2.658,1.329-4.074,3.985-4.074Z" transform="translate(-358.165 -223.27)" fill="#fff"/><path d="M539.233,255.154c2.656,0,4.074,1.416,4.074,4.074v34.007h10.1c2.746,0,4.074,1.329,4.074,4.074s-1.328,4.074-4.074,4.074H524.8c-2.656,0-4.074-1.328-4.074-4.074s1.418-4.074,4.074-4.074h10.362V263.3h-8.533c-2.744,0-4.073-1.329-4.073-4.074,0-2.658,1.329-4.074,4.073-4.074Zm4.22-17.615a5.859,5.859,0,1,1-5.819-5.819A5.9,5.9,0,0,1,543.453,237.539Z" transform="translate(-358.165 -223.27)" fill="#fff"/><path d="M605.143,259.228a4.589,4.589,0,0,1-.267,1.594L590,298.9a3.722,3.722,0,0,1-3.721,2.48h-5.933a3.689,3.689,0,0,1-3.808-2.48l-15.055-38.081a3.23,3.23,0,0,1-.355-1.594,4.084,4.084,0,0,1,4.164-4.074,3.8,3.8,0,0,1,3.718,2.656l14.348,36.134,13.9-36.134a3.8,3.8,0,0,1,3.72-2.656A4.084,4.084,0,0,1,605.143,259.228Z" transform="translate(-358.165 -223.27)" fill="#fff"/><path d="M390.61,255.154c5.018,0,8.206,3.312,8.206,8.4v37.831H363.308a4.813,4.813,0,0,1-5.143-4.929V283.427a8.256,8.256,0,0,1,7-8.148l25.507-3.572v-8.4H362.306a4.014,4.014,0,0,1-4.141-4.074c0-2.87,2.143-4.074,4.355-4.074Zm.059,38.081V279.942l-24.354,3.4v9.9Z" transform="translate(-358.165 -223.27)" fill="#fff"/><path d="M448.538,224.52h.077c1,.024,2.236,1.245,2.589,1.669l.023.028.024.026,46.664,50.433a3.173,3.173,0,0,1-.034,4.336l-4.893,5.2-6.876-8.134L446.652,230.4c-1.508-2.166-1.617-2.836-1.191-3.858a3.353,3.353,0,0,1,3.077-2.02m0-1.25a4.606,4.606,0,0,0-4.231,2.789c-.705,1.692-.2,2.88,1.349,5.1l39.493,47.722,7.789,9.214,5.853-6.221a4.417,4.417,0,0,0,.042-6.042L452.169,225.4s-1.713-2.08-3.524-2.124Z" transform="translate(-358.165 -223.27)" fill="#fff"/></svg>"""

theme_colors = Namespace(
    primary='#ed7ea7',    # DRAFT primary='#d984cc'
    secondary='#a33e6c',
    accent='#a82c64',
    dark='#4d1f48',
    positive='#22ba38',
    negative='#f50000',
    info='#31CCEC',
    warning='#9333ea'
)

# State of GUI
class GUIState:
    """State of GUI-related objects
    
        NOTE: "#" is used as a separator in GUI keys to avoid confusion with
            symbols that can be (typically) used in body/design parameter names 
            ('_', '-', etc.) 

    """
    def __init__(self) -> None:
        self.window = None

        # Pattern
        self.pattern_state = GUIPattern()

        # Pattern display constants
        self.canvas_aspect_ratio = 1500. / 900   # Millimiter paper
        self.w_rel_body_size = 0.5  # Body size as fraction of horisontal canvas axis
        self.h_rel_body_size = 0.95
        self.background_body_scale = 1 / 171.99   # Inverse of the mean_all body height from GGG
        self.background_body_canvas_center = 0.273  # Fraction of the canvas (millimiter paper)
        self.w_canvas_pad, self.h_canvas_pad = 0.011, 0.04
        self.body_outline_classes = ''   # Application of pattern&body scaling when it overflows

        # Paths setup
        # Static images for GUI
        self.path_static_img = '/img'
        app.add_static_files(self.path_static_img, './assets/img')
        
        # 3D updates
        self.path_static_3d = '/geo'
        self.garm_3d_filename = f'garm_3d_{self.pattern_state.id}.glb'
        self.local_path_3d = Path('./output/garm_3d')
        app.add_static_files(self.path_static_3d, self.local_path_3d)
        app.add_static_files('/body', './assets/bodies')

        # Elements
        self.ui_design_subtabs = {}
        self.ui_pattern_display = None
        self._async_executor = ThreadPoolExecutor(1)  

        self.pattern_state.reload_garment()
        self.stylings()
        self.layout()

    # Initial definitions
    def stylings(self):
        """Theme definition"""
        # Theme
        # Here: https://quasar.dev/style/theme-builder
        ui.colors(
            primary=theme_colors.primary,  
            secondary=theme_colors.secondary,
            accent=theme_colors.accent,
            dark=theme_colors.dark,
            positive=theme_colors.positive,
            negative=theme_colors.negative,
            info=theme_colors.info,
            warning=theme_colors.warning
        )

    # SECTION Top level layout        
    def layout(self):
        """Overall page layout"""

        # TODO License info? 

        # as % of viewport width/height
        self.h_header = 5
        self.h_params_content = 88
        self.h_garment_display = 74 
        self.w_garment_display = 65
        self.w_splitter_design = 32
        self.scene_base_resoltion = (1024, 800)

        # Helpers
        self.def_pattern_waiting()
        # TODOLOW One dialog for both? 
        self.def_design_file_dialog()
        self.def_body_file_dialog()

        # Configurator GUI
        with ui.row(wrap=False).classes(f'w-full h-[{self.h_params_content}dvh] p-0 m-0 '): 
            # Tabs
            self.def_param_tabs_layout()
            
            # Pattern visual
            self.view_tabs_layout()

        # Overall wrapping
        # NOTE: https://nicegui.io/documentation/section_pages_routing#page_layout
        with ui.header(elevated=True, fixed=False).classes(f'h-[{self.h_header}vh] items-center justify-end py-0 px-4 m-0'):
            ui.label('GarmentCode design configurator').classes('mr-auto').style('font-size: 150%; font-weight: 400')
            ui.button(
                'About the project', 
                on_click=lambda: ui.navigate.to('https://igl.ethz.ch/projects/garmentcode/', new_tab=True)
                ).props('flat color=white')
            with ui.link(target='https://arxiv.org/abs/2306.03642', new_tab=True):
                ui.html(icon_arxiv).classes('w-16 bg-transparent')
            ui.button(
                'Dataset',  # TODO Update the link once project page is out!
                on_click=lambda: ui.navigate.to('https://arxiv.org/abs/2405.17609', new_tab=True)
                ).props('flat color=white')
            with ui.link(target='https://github.com/maria-korosteleva/GarmentCode', new_tab=True):
                ui.html(icon_github).classes('w-8 bg-transparent')
        # NOTE No ui.left_drawer(), no ui.right_drawer()
        with ui.footer(fixed=False, elevated=True).classes('items-center justify-center p-0 m-0'): 
            # https://www.termsfeed.com/blog/sample-copyright-notices/
            ui.link(
                '© 2024 Interactive Geometry Lab', 
                'https://igl.ethz.ch/', 
                new_tab=True
            ).classes('text-white')

    def view_tabs_layout(self):
        """2D/3D view tabs"""
        with ui.column(wrap=False).classes(f'h-[{self.h_params_content}vh] w-full items-center'):
            with ui.tabs() as tabs: 
                self.ui_2d_tab = ui.tab('Sewing Pattern')
                self.ui_3d_tab = ui.tab('3D view')
            with ui.tab_panels(tabs, value=self.ui_2d_tab, animated=True).classes('w-full h-full items-center'):  
                with ui.tab_panel(self.ui_2d_tab).classes('w-full h-full items-center justify-center p-0 m-0'):
                    self.def_pattern_display()
                with ui.tab_panel(self.ui_3d_tab).classes('w-full h-full items-center p-0 m-0'):
                    self.def_3d_scene()

            ui.button('Download Current Garment', on_click=lambda: self.state_download()).classes('justify-self-end')

    # !SECTION
    # SECTION -- Parameter menu
    def def_param_tabs_layout(self):
        """Layout of tabs with parameters"""
        with ui.column(wrap=False).classes(f'h-[{self.h_params_content}vh]'):
            with ui.tabs() as tabs:
                self.ui_design_tab = ui.tab('Design parameters')
                self.ui_body_tab = ui.tab('Body parameters')
            with ui.tab_panels(tabs, value=self.ui_design_tab, animated=True).classes('w-full h-full items-center'):  
                with ui.tab_panel(self.ui_design_tab).classes('w-full h-full items-center p-0 m-0'):
                    self.def_design_tab()
                with ui.tab_panel(self.ui_body_tab).classes('w-full h-full items-center p-0 m-0'):
                    self.def_body_tab()

    def def_body_tab(self):
    
        # Set of buttons
        with ui.row():
            ui.button('Upload', on_click=self.ui_body_dialog.open)  
        
        self.ui_active_body_refs = {}
        self.ui_passive_body_refs = {}
        with ui.scroll_area().classes('w-full h-full p-0 m-0'): # NOTE: p-0 m-0 gap-0 dont' seem to have effect
            body = self.pattern_state.body_params
            for param in body:
                param_name = param.replace('_', ' ').capitalize()
                elem = ui.number(
                        label=param_name, 
                        value=str(body[param]), 
                        format='%.2f',
                        precision=2,
                        step=0.5,
                ).classes('text-[0.85rem]')

                if param[0] == '_':  # Info elements for calculatable parameters
                    elem.disable()
                    self.ui_passive_body_refs[param] = elem
                else:   # active elements accepting input
                    # NOTE: e.sender == UI object, e.value == new value
                    elem.on_value_change(lambda e, dic=body, param=param: self.update_pattern_ui_state(
                        dic, param, e.value, body_param=True
                    ))
                    self.ui_active_body_refs[param] = elem

    def def_flat_design_subtab(self, ui_elems, design_params, use_collapsible=False):
        """Group of design parameters"""
        for param in design_params: 
            param_name = param.replace('_', ' ').capitalize()
            if 'v' not in design_params[param]:
                ui_elems[param] = {}
                if use_collapsible:
                    with ui.expansion().classes('w-full p-0 m-0') as expansion: 
                        with expansion.add_slot('header'):
                            ui.label(f'{param_name}').classes('text-base self-center w-full h-full p-0 m-0')
                        with ui.row().classes('w-full h-full p-0 m-0'):  # Ensures correct application of style classes for children
                            self.def_flat_design_subtab(ui_elems[param], design_params[param])
                else:
                    with ui.card().classes('w-full shadow-md border m-0 rounded-md'): 
                        ui.label(f'{param_name}').classes('text-base self-center w-full h-full p-0 m-0')
                        self.def_flat_design_subtab(ui_elems[param], design_params[param])
            else:
                # Leaf value
                p_type = design_params[param]['type']
                val = design_params[param]['v']
                p_range = design_params[param]['range']
                if 'select' in p_type:
                    values = design_params[param]['range']
                    if 'null' in p_type and None not in values: 
                        values.append(None)  # NOTE: Displayable value
                    ui.label(param_name).classes('p-0 m-0 mt-2 text-stone-500 text-[0.85rem]') 
                    ui_elems[param] = ui.select(
                        values, value=val,
                        on_change=lambda e, dic=design_params, param=param: self.update_pattern_ui_state(dic, param, e.value)
                    ).classes('w-full') 
                elif p_type == 'bool':
                    ui_elems[param] = ui.switch(
                        param_name, value=val, 
                        on_change=lambda e, dic=design_params, param=param: self.update_pattern_ui_state(dic, param, e.value)
                    ).classes('text-stone-500')
                elif p_type == 'float' or p_type == 'int':
                    ui.label(param_name).classes('p-0 m-0 mt-2 text-stone-500 text-[0.85rem]')
                    ui_elems[param] = ui.slider(
                        value=val, 
                        min=p_range[0], 
                        max=p_range[1], 
                        step=0.025 if p_type == 'float' else 1,
                    ).props('snap label').classes('w-full')  \
                        .on('update:model-value', 
                            lambda e, dic=design_params, param=param: self.update_pattern_ui_state(dic, param, e.args),
                            throttle=0.5, leading_events=False)

                    # NOTE Events control: https://nicegui.io/documentation/slider#throttle_events_with_leading_and_trailing_options
                elif 'file' in p_type:
                    print(f'GUI::NotImplementedERROR::{param}::'
                          '"file" parameter type is not yet supported in Web GarmentCode. '
                          'Creation of corresponding UI element skipped'
                    )
                else:
                    print(f'GUI::WARNING::Unknown parameter type: {p_type}')
                    ui_elems[param] = ui.input(label=param_name, value=val, placeholder='Type the value',
                        validation={'Input too long': lambda value: len(value) < 20},
                        on_change=lambda e, dic=design_params, param=param: self.update_pattern_ui_state(dic, param, e.value)
                    ).classes('w-full')
                
    def def_design_tab(self):
        async def random():
            self.toggle_param_update_events(self.ui_design_refs)  # Don't react to value updates

            self.pattern_state.sample_design()
            self.update_design_params_ui_state(self.ui_design_refs, self.pattern_state.design_params)
            await self.update_pattern_ui_state()

            self.toggle_param_update_events(self.ui_design_refs)  # Re-do reaction to value updates
    
        async def default():
            self.toggle_param_update_events(self.ui_design_refs)

            self.pattern_state.restore_design(False)
            self.update_design_params_ui_state(self.ui_design_refs, self.pattern_state.design_params)
            await self.update_pattern_ui_state()

            self.toggle_param_update_events(self.ui_design_refs)

        # Set of buttons
        with ui.row():
            ui.button('Random', on_click=random)
            ui.button('Default', on_click=default)
            ui.button('Upload', on_click=self.ui_design_dialog.open)  
    
        # Design parameters
        design_params = self.pattern_state.design_params
        self.ui_design_refs = {}
        if self.pattern_state.is_design_sectioned():
            # Use tabs to represent top-level sections
            with ui.splitter(value=self.w_splitter_design).classes('w-full h-full p-0 m-0') as splitter:
                with splitter.before:
                    with ui.tabs().props('vertical').classes('w-full h-full') as tabs:
                        for param in design_params:
                            # Tab
                            self.ui_design_subtabs[param] = ui.tab(param)
                            self.ui_design_refs[param] = {}

                with splitter.after:
                    with ui.tab_panels(tabs, value=self.ui_design_subtabs['meta']).props('vertical').classes('w-full h-full p-0 m-0'):
                        for param, tab_elem in self.ui_design_subtabs.items():
                            with ui.tab_panel(tab_elem).classes('w-full h-full p-0 m-0').style('gap: 0px'): 
                                with ui.scroll_area().classes('w-full h-full p-0 m-0').style('gap: 0px'):
                                    self.def_flat_design_subtab(
                                        self.ui_design_refs[param],
                                        design_params[param],
                                        use_collapsible=(param == 'left')
                                    )
        else:
            # Simplified display of designs
            with ui.scroll_area().classes('w-full h-full p-0 m-0'):
                self.def_flat_design_subtab(
                    self.ui_design_refs,
                    design_params,
                    use_collapsible=True
                )
                            
    # !SECTION
    # SECTION -- Pattern visuals
    def def_pattern_display(self):
        """Prepare pattern display area"""
        with ui.column().classes('h-full p-0 m-0'):
            with ui.row().classes('w-full p-0 m-0 justify-between'):
                switch = ui.switch(
                    'Body Silhouette', value=True, 
                ).props('dense left-label').classes('text-stone-800')

                self.ui_self_intersect = ui.label(
                    'WARNING: Garment panels are self-intersecting!'
                ).classes('font-semibold text-purple-600 border-purple-600 border py-0 px-1.5 rounded-md') \
                .bind_visibility(self.pattern_state, 'is_self_intersecting')

            with ui.image(
                    f'{self.path_static_img}/millimiter_paper_1500_900.png'
                ).classes(f'aspect-[{self.canvas_aspect_ratio}] h-[95%] p-0 m-0')  as self.ui_pattern_bg:  
                # NOTE: Positioning: https://github.com/zauberzeug/nicegui/discussions/957 
                with ui.row().classes('w-full h-full p-0 m-0 bg-transparent relative top-[0%] left-[0%]'):
                    self.body_outline_classes = 'bg-transparent h-full absolute top-[0%] left-[0%] p-0 m-0'
                    self.ui_body_outline = ui.image(f'{self.path_static_img}/ggg_outline_mean_all.svg') \
                        .classes(self.body_outline_classes) 
                    switch.bind_value(self.ui_body_outline, 'visible')
                
                # NOTE: ui.row allows for correct classes application (e.g. no padding on svg pattern)
                with ui.row().classes('w-full h-full p-0 m-0 bg-transparent relative'):
                    # Automatically updates from source
                    self.ui_pattern_display = ui.interactive_image(
                        ''
                    ).classes('bg-transparent p-0 m-0')                    

    # !SECTION
    # SECTION 3D view
    def create_lights(self, scene:ui.scene, intensity=30.0):
        light_positions = np.array([
            [1.60614, 1.23701, 1.5341,],
            [1.31844, -2.52238, 1.92831],
            [-2.80522, 2.34624, 1.2594],
            [0.160261, 3.52215, 1.81789],
            [-2.65752, -1.26328, 1.41194]
        ])
        light_colors = [
            '#ffffff',
            '#ffffff',
            '#ffffff',
            '#ffffff',
            '#ffffff'
        ]
        z_dirs = np.arctan2(light_positions[:, 1], light_positions[:, 0])

        # Add lights to the scene
        for i in range(len(light_positions)):
            scene.spot_light(
                color=light_colors[i], intensity=intensity,
                angle=np.pi,
                ).rotate(0., 0., -z_dirs[i]).move(light_positions[i][0], light_positions[i][1], light_positions[i][2])

    def create_camera(self, cam_location, fov, scale=1.):
        camera = ui.scene.perspective_camera(fov=fov)
        camera.x = cam_location[0] * scale
        camera.y = cam_location[1] * scale
        camera.z = cam_location[2] * scale

        # direction
        camera.look_at_x = 0
        camera.look_at_y = 0
        camera.look_at_z = cam_location[2] * scale * 2/3

        return camera

    def def_3d_scene(self):
        y_fov = np.pi / 6. 
        camera_location = [0, -200., 1.25]  
        bg_color='#ffffff'

        def body_visibility(value):
            self.ui_body_3d.visible(value)

        with ui.row().classes('w-full p-0 m-0 justify-between items-center'):
            self.ui_body_3d_switch = ui.switch(
                'Body Silhouette', 
                value=True, 
                on_change=lambda e: body_visibility(e.value) 
            ).props('dense left-label').classes('text-stone-800')

            ui.button('Drape current design', on_click=lambda: self.update_3d_scene())

            ui.label(
                'INFO: it takes a few minutes'
            ).classes(f'font-semibold text-[{theme_colors.primary}] border-[{theme_colors.primary}] '
                    'border py-0 px-1.5 rounded-md')

        camera = self.create_camera(camera_location, y_fov)
        with ui.scene(
            width=self.scene_base_resoltion[0], 
            height=self.scene_base_resoltion[1], 
            camera=camera, 
            grid=False, 
            background_color=bg_color   
            ).classes(f'w-[{self.w_garment_display}vw] h-[90%] p-0 m-0') as self.ui_3d_scene:
            # Lights setup
            self.create_lights(self.ui_3d_scene, intensity=60.)
            # NOTE: texture is there, just needs a better setup
            self.ui_garment_3d = None
            # FIXME body is mixing with the garment..
            # TODOLOW Update body model to a correct shape
            self.ui_body_3d = self.ui_3d_scene.stl(
                    '/body/mean_all.stl' 
                ).rotate(np.pi / 2, 0., 0.).material(color='#000000')

    # !SECTION
    # SECTION -- Other UI details
    def def_pattern_waiting(self):
        """Define the waiting splashcreen with spinner 
            (e.g. waiting for a pattern to update)"""
        
        # NOTE: the screen darkens because of the shadow
        with ui.dialog(value=False).props(
            'persistent maximized'
        ) as self.spin_dialog, ui.card().classes('bg-transparent'):
            # Styles https://quasar.dev/vue-components/spinners
            ui.spinner('hearts', size='15em').classes('fixed-center')   # NOTE: 'dots' 'ball' 

    def def_body_file_dialog(self):
        """ Dialog for loading parameter files (body)
        """
        async def handle_upload(e: events.UploadEventArguments):
            param_dict = yaml.safe_load(e.content.read())['body']

            self.toggle_param_update_events(self.ui_active_body_refs)

            self.pattern_state.set_new_body_params(param_dict)
            self.update_body_params_ui_state(self.ui_active_body_refs)            
            await self.update_pattern_ui_state()

            self.toggle_param_update_events(self.ui_active_body_refs)

            ui.notify(f'Successfully applied {e.name}')
            self.ui_body_dialog.close()

        with ui.dialog() as self.ui_body_dialog, ui.card().classes('items-center'):
            # NOTE: https://www.reddit.com/r/nicegui/comments/1393i2f/file_upload_with_restricted_types/
            ui.upload(
                label='Body parameters .yaml or .json',  
                on_upload=handle_upload
            ).classes('max-w-full').props('accept=".yaml,.json"')  

            ui.button('Close without upload', on_click=self.ui_body_dialog.close)

    def def_design_file_dialog(self):
        """ Dialog for loading parameter files (design)
        """

        async def handle_upload(e: events.UploadEventArguments):
            param_dict = yaml.safe_load(e.content.read())['design']

            self.toggle_param_update_events(self.ui_design_refs)  # Don't react to value updates

            self.pattern_state.set_new_design(param_dict)
            self.update_design_params_ui_state(self.ui_design_refs, self.pattern_state.design_params)
            await self.update_pattern_ui_state()

            self.toggle_param_update_events(self.ui_design_refs)  # Re-enable reaction to value updates

            ui.notify(f'Successfully applied {e.name}')
            self.ui_design_dialog.close()

        with ui.dialog() as self.ui_design_dialog, ui.card().classes('items-center'):
            # NOTE: https://www.reddit.com/r/nicegui/comments/1393i2f/file_upload_with_restricted_types/
            ui.upload(
                label='Design parameters .yaml or .json',  
                on_upload=handle_upload
            ).classes('max-w-full').props('accept=".yaml,.json"')  

            ui.button('Close without upload', on_click=self.ui_design_dialog.close)

    # !SECTION
    # SECTION -- Event callbacks
    async def update_pattern_ui_state(self, param_dict=None, param=None, new_value=None, body_param=False):
        """UI was updated -- update the state of the pattern parameters and visuals"""
        # NOTE: Fixing to the "same value" issue in lambdas 
        # https://github.com/zauberzeug/nicegui/wiki/FAQs#why-have-all-my-elements-the-same-value
   
        print('INFO::Updating pattern...')

        # Update the values
        if param_dict is not None:
            if body_param:
                param_dict[param] = new_value
            else:
                param_dict[param]['v'] = new_value
                self.pattern_state.is_in_3D = False   # Design param changes -> 3D model is not synced with the param
 
        try:
            if not self.pattern_state.is_slow_design(): 
                # Quick update
                self._sync_update_state()
                return

            # Display waiting spinner untill getting the result
            # NOTE Splashscreen solution to block users from modifying params while updating
            # https://github.com/zauberzeug/nicegui/discussions/1988

            self.spin_dialog.open()   
            # NOTE: Using threads for async call 
            # https://stackoverflow.com/questions/49822552/python-asyncio-typeerror-object-dict-cant-be-used-in-await-expression
            self.loop = asyncio.get_event_loop()
            await self.loop.run_in_executor(self._async_executor, self._sync_update_state)
            
            self.spin_dialog.close()

        except KeyboardInterrupt as e:
            raise e
        except BaseException as e:
            traceback.print_exc()
            print(e)
            self.spin_dialog.close()  # If open
            ui.notify(
                'Failed to generate pattern correctly. Try different parameter values',
                type='negative',
                close_button=True,
                position='center'
            )

    def _sync_update_state(self):
        # Update derivative body values (just in case)
        # TODOLOW only do that on body value updates
        self.pattern_state.body_params.eval_dependencies()
        self.update_body_params_ui_state(self.ui_passive_body_refs) # Display evaluated dependencies

        # Update the garment
        # Sync left-right for easier editing
        self.pattern_state.sync_left(with_check=True)

        # NOTE This is the slow part 
        self.pattern_state.reload_garment()

        # TODOLOW the pattern is floating around when collars are added.. 
        # Update display
        if self.ui_pattern_display is not None:

            if self.pattern_state.svg_filename:
                # Re-align the canvas and body with the new pattern
                p_bbox_size = self.pattern_state.svg_bbox_size
                p_bbox = self.pattern_state.svg_bbox

                # Margin calculations w.r.t. canvas size
                # s.t. the pattern scales correctly
                w_shift = abs(p_bbox[0])  # Body feet location in width direction w.r.t top-left corner of the pattern
                m_top = (1. - abs(p_bbox[2]) * self.background_body_scale) * self.h_rel_body_size + (1. - self.h_rel_body_size) / 2 
                m_left = self.background_body_canvas_center - w_shift * self.background_body_scale * self.w_rel_body_size
                m_right = 1 - m_left - p_bbox_size[0] * self.background_body_scale * self.w_rel_body_size
                m_bottom = 1 - m_top - p_bbox_size[1] * self.background_body_scale * self.h_rel_body_size

                # Canvas padding adjustment
                m_top -= self.h_canvas_pad
                m_left -= self.w_canvas_pad
                m_right += self.w_canvas_pad  # preserve evaluated width
                m_bottom -= self.h_canvas_pad

                # New placement
                if m_top < 0 or m_bottom < 0 or m_left < 0 or m_right < 0:
                    # Calculate the fraction
                    scale_margin = 1.2
                    y_top_scale = abs(min(m_top * scale_margin, 0.)) + 1.
                    y_bot_scale = 1. + abs(min(m_bottom * scale_margin, 0.))
                    x_left_scale = abs(min(m_left * scale_margin, 0.)) + 1.
                    x_right_scale = abs(min(m_right * scale_margin, 0.)) + 1.
                    scale = min(1. / y_top_scale, 1. / y_bot_scale, 1. / x_left_scale, 1. / x_right_scale)

                    # Rescale the body
                    self.ui_body_outline.classes(
                        replace=self.body_outline_classes + f' origin-center scale-[{scale}]'
                    )

                    # Recalculate positioning & width
                    body_center = 0.5 - self.background_body_canvas_center
                    m_top = (1. - abs(p_bbox[2]) * self.background_body_scale) * self.h_rel_body_size * scale + (1. - self.h_rel_body_size * scale) / 2 
                    m_left = (0.5 - body_center * scale) - w_shift * self.background_body_scale * self.w_rel_body_size * scale
                    m_right = 1 - m_left - p_bbox_size[0] * self.background_body_scale * self.w_rel_body_size * scale

                    # Canvas padding adjustment
                    # TODOLOW For some reason top adjustment is not needed here: m_top -= self.h_canvas_pad * scale
                    m_left -= self.w_canvas_pad * scale
                    m_right += self.w_canvas_pad * scale

                else:  # Display normally 
                    # Remove body transforms if any were applied
                    self.ui_body_outline.classes(replace=self.body_outline_classes)

                # New pattern image
                self.ui_pattern_display.set_source(
                    str(self.pattern_state.svg_path()) if self.pattern_state.svg_filename else '')
                self.ui_pattern_display.classes(
                        replace=f"""bg-transparent p-0 m-0
                                absolute 
                                left-[{m_left * 100}%]
                                top-[{m_top * 100}%] 
                                w-[{(1. - m_right - m_left) * 100}%]
                                height-auto
                        """)  
                    
            else:
                # Restore default state
                self.ui_pattern_display.set_source('')
                self.ui_body_outline.classes(replace=self.body_outline_classes)

    def update_design_params_ui_state(self, ui_elems, design_params):
        """Sync ui params with the current state of the design params"""
        for param in design_params: 
            if 'v' not in design_params[param]:
                self.update_design_params_ui_state(ui_elems[param], design_params[param])
            else:
                ui_elems[param].value = design_params[param]['v']

    def toggle_param_update_events(self, ui_elems):
        """Enable/disable event handling on the ui elements related to GarmentCode parameters"""
        for param in ui_elems:
            if isinstance(ui_elems[param], dict):
                self.toggle_param_update_events(ui_elems[param])
            else:
                if ui_elems[param].is_ignoring_events:  # -> disabled
                    ui_elems[param].enable()
                else:
                    ui_elems[param].disable()

    def update_body_params_ui_state(self, ui_body_refs):
        """Sync ui params with the current state of the body params"""
        for param in ui_body_refs: 
            ui_body_refs[param].value = self.pattern_state.body_params[param]

    async def update_3d_scene(self):
        """According the whatever pattern current state"""

        print('INFO::Updating 3D...')

        # Cleanup 
        if self.ui_garment_3d is not None:
            self.ui_garment_3d.delete()
            self.ui_garment_3d = None
        
        if not self.pattern_state.svg_filename:
            print('INFO::Current garment is empty, skipped 3D update')
            ui.notify('Current garment is empty. Chose a design to start simulating!')
            self.ui_body_3d.visible(True)
            self.ui_body_3d_switch.set_value(True)
            return

        try:
            # Display waiting spinner untill getting the result
            # NOTE Splashscreen solution to block users from modifying params while updating
            # https://github.com/zauberzeug/nicegui/discussions/1988

            self.spin_dialog.open()   
            self.ui_3d_scene.set_visibility(False)
            # NOTE: Using threads for async call 
            # https://stackoverflow.com/questions/49822552/python-asyncio-typeerror-object-dict-cant-be-used-in-await-expression
            self.loop = asyncio.get_event_loop()
            await self.loop.run_in_executor(self._async_executor, self._sync_update_3d)

            # Update ui
            # https://github.com/zauberzeug/nicegui/discussions/1269
            with self.ui_3d_scene:
                self.ui_garment_3d = self.ui_3d_scene.gltf(
                            f'geo/{self.garm_3d_filename}', 
                        ).scale(0.01).rotate(np.pi / 2, 0., 0.).material(side='double')  # NOTE the latter seem to have no effect
            
            # Body invisible by default due to occlusion artifacts
            self.ui_body_3d.visible(False)
            self.ui_body_3d_switch.set_value(False)

            # Show the result! =)
            self.ui_3d_scene.set_visibility(True)
            self.spin_dialog.close()

        except KeyboardInterrupt as e:
            raise e
        except BaseException as e:
            traceback.print_exc()
            print(e)
            self.ui_3d_scene.set_visibility(True)
            self.spin_dialog.close()  # If open
            ui.notify(
                'Failed to generate 3D model correctly. Try different parameter values',
                type='negative',
                close_button=True,
                position='center'
            )
    
    def _sync_update_3d(self):
        """Update 3d model"""

        # Run simulation
        path, filename = self.pattern_state.drape_3d()

        # NOTE: The files will be available publically at the static point
        # However, we cannot do much about it, since it won't be available for the interface otherwise
        shutil.copy2(path / filename, self.local_path_3d / self.garm_3d_filename)

    # !SECTION

    def state_download(self):
        """Download current state of a garment"""
        archive_path = self.pattern_state.save()
        ui.download(archive_path, f'Configured_design_{datetime.now().strftime("%y%m%d-%H-%M-%S")}.zip')
