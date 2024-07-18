"""Callback functions & State info for Sewing Pattern Configurator """

# NOTE: NiceGUI reference: https://nicegui.io/

from pathlib import Path
import yaml
import traceback

from nicegui import ui, app, events

# Async execution of regular functions
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Custom
from .gui_pattern import GUIPattern

icon_image_b64 = 'data:image/png;base64,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'

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
        self.canvas_aspect_ratio = 1500 / 900   # Millimiter paper
        self.w_rel_body_size = 0.5  # Body size as fraction of horisontal canvas axis
        self.h_rel_body_size = 0.95
        self.background_body_scale = 1 / 171.99   # Inverse of the mean_all body height from GGG
        self.background_body_canvas_center = 0.27  # Fraction of the canvas (millimiter paper)
        self.w_canvas_pad, self.h_canvas_pad = 0.011, 0.04

        # Elements
        self.ui_design_subtabs = {}
        self.ui_pattern_display = None
        self._async_executor = ThreadPoolExecutor(1)  

        self.pattern_state.reload_garment()
        self.stylings()
        self.layout()

        # New
        # TODO Separate params per user session! 
        # (probably using internal page for configurator will be enough)
        # Or saving to user/browser storage??
        # TODO 3D scene visualisation

    # Start the GUI
    def run(self):
        ui.run(
            reload=False,
            favicon=icon_image_b64,
            title='GarmentCode'
        )

    # Initial definitions
    def stylings(self):
        """Theme definition"""
        # Theme
        # Here: https://quasar.dev/style/theme-builder
        ui.colors(
            # DRAFT primary='#d984cc'
            primary='#ed7ea7',  
            secondary='#a33e6c',
            accent='#a82c64',
            dark='#4d1f48',
            positive='#22ba38',
            negative='#f50000',
            info='#31CCEC',
            warning='#9333ea'
        )
        
    def layout(self):
        """Overall page layout"""

        # TODO License info? 

        # as % of viewport width/height
        self.h_header = 5
        self.h_footer = 3
        self.h_content = 85
        self.w_pattern_display = 65
        self.w_splitter_design = 32

        # Helpers
        self.def_pattern_waiting()
        # TODOLOW One dialog for both? 
        self.def_design_file_dialog()
        self.def_body_file_dialog()

        # Configurator GUI
        self.path_static_img = '/img'
        self.path_ui_pattern = '/tmp_pattern'
        app.add_static_files(self.path_static_img, './assets/img')
        app.add_static_files(self.path_ui_pattern, self.pattern_state.tmp_path)
        with ui.row(wrap=False).classes('w-full h-full'):  
            # Tabs
            self.def_param_tabs_layout()
            
            # Pattern visual
            self.def_pattern_display()

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
                'Dataset', 
                on_click=lambda: ui.navigate.to('https://arxiv.org/abs/2405.17609', new_tab=True)
                ).props('flat color=white')
            with ui.link(target='https://github.com/maria-korosteleva/GarmentCode', new_tab=True):
                ui.html(icon_github).classes('w-8 bg-transparent')
        # NOTE No ui.left_drawer(), no ui.right_drawer()
        with ui.footer(fixed=False, elevated=True).classes(f'h-[{self.h_footer}vh] items-center justify-center p-0 m-0'):
            # https://www.termsfeed.com/blog/sample-copyright-notices/
            ui.link(
                '© 2024 Interactive Geometry Lab', 
                'https://igl.ethz.ch/', 
                new_tab=True
            ).classes('text-white')

    # !SECTION
    # SECTION -- Parameter menu
    def def_param_tabs_layout(self):
        """Layout of tabs with parameters"""
        with ui.column(wrap=False).classes(f'h-[{self.h_content}vh]'):
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
        with ui.column().classes('w-full items-center p-0 m-0'): 
            with ui.column().classes('p-0 m-0'):
                with ui.row().classes('w-full p-0 m-0 justify-between'):
                    switch = ui.switch(
                        'Body Silhouette', value=True, 
                    ).props('dense left-label').classes('text-stone-800')

                    self.ui_self_intersect = ui.label(
                        'WARNING: Garment panels are self-intersecting!'
                    ).classes('font-semibold text-purple-600 border-purple-600 border py-0 px-1.5 rounded-md') \
                    .bind_visibility(self.pattern_state, 'is_self_intersecting')

                with ui.image(f'{self.path_static_img}/millimiter_paper_1500_900.png').classes(f'w-[{self.w_pattern_display}vw] p-0 m-0') as self.ui_pattern_bg:       
                    # NOTE: Positioning: https://github.com/zauberzeug/nicegui/discussions/957 
                    with ui.row().classes('w-full h-full p-0 m-0 bg-transparent absolute top-[0%] left-[0%]'):
                        self.ui_body_outline = ui.image(f'{self.path_static_img}/ggg_outline_mean_all.svg') \
                            .classes('bg-transparent h-full absolute top-[0%] left-[0%] p-0 m-0') 
                        switch.bind_value(self.ui_body_outline, 'visible')
                    
                    # NOTE: ui.row allows for correct classes application (e.g. no padding on svg pattern)
                    with ui.row().classes('w-full h-full p-0 m-0 bg-transparent'):
                        # Automatically updates from source
                        self.ui_pattern_display = ui.interactive_image(
                            ''
                        ).classes('bg-transparent p-0 m-0')                    
                
            ui.button('Download Current Garment', on_click=lambda: self.state_download())

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
   
        # DEBUG
        print('Updating pattern')

        # Update the values
        if param_dict is not None:
            if body_param:
                param_dict[param] = new_value
            else:
                param_dict[param]['v'] = new_value

        # Quick update
        try:
            if not self.pattern_state.is_slow_design(): 
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
        # TODO: overflowing elements -- one can check that margins are negative
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

                # Canvas padding adjustment
                m_top -= self.h_canvas_pad
                m_left -= self.w_canvas_pad
                m_right += self.w_canvas_pad

                # DEBUG
                print('Garment box ', p_bbox_size)
                print(p_bbox)
                # print('margins ', m_top, m_top / self.canvas_aspect_ratio, m_bottom, m_bottom / self.canvas_aspect_ratio)
                # print('LR ', m_left, m_right)
                print(f'final percents ml-[{(m_left * 100)}%] '
                      f' mr-[{(m_right * 100)}%] ' 
                      f' mt-[{(m_top * 100 / self.canvas_aspect_ratio)}%]'
                )

                # New pattern image
                self.ui_pattern_display.set_source(
                    f'{self.path_ui_pattern}/' + self.pattern_state.svg_filename if self.pattern_state.svg_filename else '')
                # New placement
                # mb-[{m_bottom * 100 / self.canvas_aspect_ratio}%]
                self.ui_pattern_display.classes(
                    replace=f"""bg-transparent p-0
                            mt-[{m_top * 100 / self.canvas_aspect_ratio}%]
                            ml-[{m_left * 100}%] 
                            mr-[{m_right * 100}%] 
                            mb-auto
                            absolute top-[0%] left-[0%]
                    """)
            else:
                # TODO restore default body placement if needed
                self.ui_pattern_display.set_source('')

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

    def state_download(self):
        """Download current state of a garment"""
        archive_path = self.pattern_state.save()
        ui.download(archive_path)

    # !SECTION