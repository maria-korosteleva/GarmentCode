"""Callback functions & State info for Sewing Pattern Configurator """

# NOTE: NiceGUI reference: https://nicegui.io/

from copy import copy
from pathlib import Path
import time

from nicegui import ui, app
from nicegui.events import ValueChangeEventArguments

from .gui_pattern import GUIPattern

# Async execution of regular functions
from concurrent.futures import ThreadPoolExecutor
import asyncio

icon_image_b64 = 'data:image/png;base64,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'

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
        self.background_body_scale = 1 / 171.99   # Inverse of the mean_all body height from GGG
        self.background_body_canvas_center = 0.27  # Fraction of the canvas (millimiter paper)
        self.w_svg_pad, self.h_svg_pad = 5, 5   # compensation for automatic svg padding, ~okay on big screens

        # Elements
        self.ui_design_subtabs = {}
        self.ui_pattern_display = None
        self._async_executor = ThreadPoolExecutor(1)  

        # TODO Callbacks on buttons and file loads
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
        # TODO Develop the theme more
        ui.colors(primary='#d984cc')
        
    def layout(self):
        """Overall page layout"""

        # TODO About us page
        # TODO Link to project page
        # TODO License info? 
        # TODO error on mobile/small screens? (Or put the controls in the drawer -- figure it out?)
        # TODO Link to GitHub
        # TODO Randomize & Restore default buttons

        # as % of viewport width/height
        self.h_header = 5
        self.h_footer = 3
        self.h_content = 85
        self.w_pattern_display = 65  # TODO Not great for height control though..

        # Helpers
        self.def_pattern_waiting()

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
        with ui.header(elevated=True, fixed=False).classes(f'h-[{self.h_header}vh] items-center justify-between py-0 px-4 m-0'):
            ui.label('GarmentCode design configurator').style('font-size: 150%; font-weight: 400')
            ui.button(on_click=lambda: right_drawer.toggle(), icon='menu').props('flat color=white')
        # DRAFT No ui.left_drawer().classes('w-[50vw]'):
        with ui.right_drawer(fixed=False, value=False).props('bordered') as right_drawer:
            ui.label('Menu with useful links')
        with ui.footer(fixed=False, elevated=True).classes(f'h-[{self.h_footer}vh] items-center justify-center p-0 m-0'):
            ui.label('Future copyright message IGL (c)')   # TODO 

    # SECTION -- Parameter menu
    def def_param_tabs_layout(self):
        """Layout of tabs with parameters"""
        # TODOLOW Make collapsible? 
        with ui.column(wrap=False).classes(f'h-[{self.h_content}vh]'):
            with ui.tabs() as tabs:
                self.ui_design_tab = ui.tab('Design parameters')
                self.ui_body_tab = ui.tab('Body parameters')
            with ui.tab_panels(tabs, value=self.ui_design_tab, animated=True):  
                with ui.tab_panel(self.ui_design_tab).classes('items-center p-0 m-0'):
                    self.def_design_tab()
                with ui.tab_panel(self.ui_body_tab).classes('items-center p-0 m-0'):
                    self.def_body_tab()

    def def_body_tab(self):
    
        # TODO selector of available options + upload is one of them
        # NOTE: https://www.reddit.com/r/nicegui/comments/1393i2f/file_upload_with_restricted_types/
        self.ui_body_file = ui.upload(
            label=str(self.pattern_state.body_file.name),  
            on_upload=lambda e: ui.notify(f'Uploaded {e.name}')
        ).classes('max-w-full').props('accept=".yaml,.json"')  
        
        self.body_elems = []
        with ui.scroll_area().classes(f'w-full h-[{self.h_content - 10}vh]'):   # NOTE: p-0 m-0 gap-0 dont' seem to have effect
            body = self.pattern_state.body_params
            for param in body:
                # TODOLOW Squish a bit -- too long (failed to figure out)
                elem = ui.number(
                        label=param, 
                        value=str(body[param]), 
                        format='%.2f',
                        precision=2,
                        step=0.5,
                        # NOTE: e.sender == UI object, e.value == new value
                        on_change=lambda e, dic=body, param=param: self.update_pattern_ui_state(dic, param, e.value, body_param=True)
                        ) 

                if param[0] == '_':
                    elem.disable()

    def def_flat_design_subtab(self, ui_elems, design_params, use_collapsible=False):
        """Group of design parameters"""
        for param in design_params: 
            if 'v' not in design_params[param]:
                # TODOLOW Maybe use expansion for all?
                ui_elems[param] = {}
                if use_collapsible:
                    # TODO font size?
                    with ui.expansion(f'{param}:').classes('w-full'):
                        self.def_flat_design_subtab(ui_elems[param], design_params[param])
                else:
                    # TODO Header of the card!
                    with ui.card().classes('w-full'): 
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
                    ui_elems[param] = ui.select(
                        values, value=val,
                        on_change=lambda e, dic=design_params, param=param: self.update_pattern_ui_state(dic, param, e.value)
                    ).classes('w-full') 
                elif p_type == 'bool':
                    ui_elems[param] = ui.switch(
                        param, value=val, 
                        on_change=lambda e, dic=design_params, param=param: self.update_pattern_ui_state(dic, param, e.value)
                    )
                elif p_type == 'float' or p_type == 'int':
                    ui.label(param)
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
                    default_path = Path(design_params[param]['v'])
                    # FIXME .bind_value(design_params[param], 'v')  -- doesn't work! (and also -- not a great idea)
                    ftype = p_type.split('_')[-1]
                    ui_elems[param] = ui.upload(
                        label=str(default_path),
                        on_upload=lambda: self.update_pattern_ui_state()
                    ).classes('max-w-full').props(f'accept=".{ftype}"')
                else:
                    print(f'GUI::WARNING::Unknown parameter type: {p_type}')
                    ui_elems[param] = ui.input(label=param, value=val, placeholder='Type the value',
                        validation={'Input too long': lambda value: len(value) < 20},
                        on_change=lambda e, dic=design_params, param=param: self.update_pattern_ui_state(dic, param, e.value)
                    ).classes('w-full')
                
    def def_design_tab(self):
        # TODO Upload as a dialog
        # NOTE: https://www.reddit.com/r/nicegui/comments/1393i2f/file_upload_with_restricted_types/
        # self.ui_design_file = ui.upload(
        #     label=str(self.pattern_state.design_file.name),  
        #     on_upload=lambda e: ui.notify(f'Uploaded {e.name}')
        # ).classes('max-w-full').props('accept=".yaml,.json"')  

        async def random():
            self.toggle_design_param_update_events(self.ui_design_refs)  # Don't react to value updates

            self.pattern_state.sample_design(False)
            self.update_design_params_ui_state(self.ui_design_refs, self.pattern_state.design_params)
            await self.update_pattern_ui_state()

            self.toggle_design_param_update_events(self.ui_design_refs)  # Re-do reaction to value updates
    
        async def default():
            self.toggle_design_param_update_events(self.ui_design_refs)

            self.pattern_state.restore_design(False)
            self.update_design_params_ui_state(self.ui_design_refs, self.pattern_state.design_params)
            await self.update_pattern_ui_state()

            self.toggle_design_param_update_events(self.ui_design_refs)


        # Set of buttons
        with ui.row():
            ui.button('Random', on_click=random)
            ui.button('Default', on_click=default)
            ui.button('Upload')   # TODO open a dialog with file uploads for both body and design
    
        # Design parameters
        design_params = self.pattern_state.design_params
        self.ui_design_refs = {}
        with ui.splitter(value=32).classes(f'w-full h-[{self.h_content - 10}vh] p-0 m-0') as splitter:
            with splitter.before:
                with ui.tabs().props('vertical').classes('w-full') as tabs:
                    for param in design_params:
                        if 'v' in design_params[param]:
                            # TODO Error message
                            # sg.popup_error_with_traceback(
                            #     f'Leaf parameter on top level of design hierarchy: {param}!!'
                            # )
                            continue
                        # Tab
                        self.ui_design_subtabs[param] = ui.tab(param)
                        self.ui_design_refs[param] = {}

            with splitter.after:
                with ui.tab_panels(tabs, value=self.ui_design_subtabs['meta']).props('vertical').classes('w-full'):  # DRAFT h-full
                    for param, tab_elem in self.ui_design_subtabs.items():
                        with ui.tab_panel(tab_elem).classes('p-0 m-0'): 
                            with ui.scroll_area().classes(f'w-full h-[{self.h_content - 19}vh] p-0 m-0'):
                                self.def_flat_design_subtab(
                                    self.ui_design_refs[param],
                                    design_params[param],
                                    use_collapsible=(param == 'left')
                                )
                            
    # SECTION -- Pattern visuals
    def def_pattern_display(self):
        """Prepare pattern display area"""
        with ui.column().classes('w-full items-center p-0 m-0'): 
            with ui.column().classes('p-0 m-0'):
                switch = ui.switch(
                    'Body Silhouette', value=True, 
                ).props('dense left-label').classes('text-stone-800')
                with ui.image(f'{self.path_static_img}/millimiter_paper_1500_900.png').classes(f'w-[{self.w_pattern_display}vw]') as self.ui_pattern_bg:
                    self.ui_body_outline = ui.image(f'{self.path_static_img}/ggg_outline_mean_all.svg') \
                        .classes('bg-transparent h-full overflow-visible absolute top-[0%] left-[0%]') 
                    switch.bind_value(self.ui_body_outline, 'visible')
                    
                    # NOTE: Positioning: https://github.com/zauberzeug/nicegui/discussions/957 
                    
                    # NOTE: Automatically updates from source
                    self.ui_pattern_display = ui.interactive_image(
                        ''
                    ).classes('bg-transparent p-0 m-0') 
                
            # TODO Add downloadable content (with timestamp)
            ui.button('Download Current Garment', on_click=lambda: ui.download('https://nicegui.io/logo.png'))

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

    # SECTION -- Event callbacks
    # TODO Is this a pattern_state function?
    async def update_pattern_ui_state(self, param_dict=None, param=None, new_value=None, body_param=False):
        """UI was updated -- update the state of the pattern parameters and visuals"""

        # NOTE: Fix to the "same value" issue in lambdas 
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

    def _sync_update_state(self):
        # Update derivative body values (just in case)
        # TODOLOW only do that on body value updates
        # TODOLOW: The following two are fast and can be executed without async
        self.pattern_state.body_params.eval_dependencies()

        # Update the garment
        # Sync left-right for easier editing
        self.pattern_state.sync_left(with_check=True)

        # NOTE This is the slow part 
        self.pattern_state.reload_garment()

        # Update display
        if self.ui_pattern_display is not None:

            if self.pattern_state.svg_filename:
                # Re-align the canvas and body with the new pattern
                p_bbox_size = self.pattern_state.svg_bbox_size
                p_bbox = self.pattern_state.svg_bbox

                # Attempt on fixing the svg padding 
                # TODO this should be scaling-independent somehow (applies after, it seems)
                # it grows w.r.t. viepowt, constand w.r.t screen size
                # TODO Github issue for NiceGUI team
                p_bbox_size[0] += self.w_svg_pad * 2
                p_bbox_size[1] += self.h_svg_pad * 2
                p_bbox[0] -= self.w_svg_pad
                p_bbox[1] += self.w_svg_pad
                p_bbox[2] -= self.h_svg_pad
                p_bbox[3] += self.h_svg_pad

                # FIXME overflowing elements -- one can check that margins are negative

                # Margin calculations w.r.t. canvas size
                # s.t. the pattern scales correctly
                w_shift = abs(p_bbox[0])  # Body feet location in width direction w.r.t top-left corner of the pattern
                h_shift = abs(p_bbox[3])  # Body feet location in height direction w.r.t top-left corner of the pattern
                m_top = 1 - (h_shift + p_bbox_size[1]) * self.background_body_scale - 0.01
                m_left = self.background_body_canvas_center - w_shift * self.background_body_scale * self.w_rel_body_size
                m_right = 1 - m_left - p_bbox_size[0] * self.background_body_scale * self.w_rel_body_size

                self.ui_pattern_display.set_source(
                    f'{self.path_ui_pattern}/' + self.pattern_state.svg_filename if self.pattern_state.svg_filename else '')
            
                self.ui_pattern_display.classes(
                    replace=f"""bg-transparent p-0
                            mt-[{int(m_top * 100 / self.canvas_aspect_ratio)}%]
                            ml-[{int(m_left * 100)}%] 
                            mr-[{int(m_right * 100)}%] 
                            object-contain
                    """)
            else:
                # TODO restore default body placement
                self.ui_pattern_display.set_source('')


    def update_design_params_ui_state(self, ui_elems, design_params):
        """Sync ui params with the current state of the design params"""
        for param in design_params: 
            if 'v' not in design_params[param]:
                self.update_design_params_ui_state(ui_elems[param], design_params[param])
            else:
                ui_elems[param].value = design_params[param]['v']

    def toggle_design_param_update_events(self, ui_elems):
        """Enable/disable event handling on the ui elements related to GarmentCode parameters"""
        for param in ui_elems:
            if isinstance(ui_elems[param], dict):
                self.toggle_design_param_update_events(ui_elems[param])
            else:
                if ui_elems[param].is_ignoring_events:  # -> disabled
                    ui_elems[param].enable()
                else:
                    ui_elems[param].disable()