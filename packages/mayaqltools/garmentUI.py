"""
    Maya interface for editing & testing patterns files
    * Maya 2022+
    * Qualoth
"""

# Basic
from functools import partial
from datetime import datetime
import os
import numpy as np

# Maya
from maya import cmds
import maya.mel as mel

# My modules
import mayaqltools as mymaya
import customconfig


# -------- Main call - Draw the UI -------------
def start_GUI():
    """Initialize interface"""

    # Init state
    state = State()  

    # init window
    window_width = 450
    main_offset = 10
    win = cmds.window(
        title="Garment Viewer", width=window_width,
        closeCommand=win_closed_callback, 
        topEdge=15
    )
    cmds.columnLayout(columnAttach=('both', main_offset), rowSpacing=10, adj=1)

    # ------ Draw GUI -------
    # Pattern load
    text_button_group(template_field_callback, state, label='Pattern spec: ', button_label='Load')
    # body load
    text_button_group(load_body_callback, state, label='Body file: ', button_label='Load')
    # props load
    text_button_group(load_props_callback, state, label='Properties: ', button_label='Load')
    # scene setup load
    text_button_group(load_scene_callback, state, label='Scene: ', button_label='Load')
    # separate
    cmds.separator()

    # Pattern description 
    state.pattern_layout = cmds.columnLayout(
        columnAttach=('both', 0), rowSpacing=main_offset, adj=1)
    cmds.text(label='<pattern_here>', al='left')
    cmds.setParent('..')
    # separate
    cmds.separator()

    # Operations
    equal_rowlayout(5, win_width=window_width, offset=(main_offset / 2))
    cmds.button(label='Reload Spec', backgroundColor=[255 / 256, 169 / 256, 119 / 256], 
                command=partial(reload_garment_callback, state))
    sim_button = cmds.button(label='Start Sim', backgroundColor=[227 / 256, 255 / 256, 119 / 256])
    cmds.button(sim_button, edit=True, 
                command=partial(start_sim_callback, sim_button, state))
    collisions_button = cmds.button(label='Collisions', backgroundColor=[250 / 256, 200 / 256, 119 / 256])
    cmds.button(collisions_button, edit=True, 
                command=partial(check_collisions_callback, collisions_button, state))
    segm_button = cmds.button(label='Segmentation', backgroundColor=[150 / 256, 225 / 256, 80 / 256])
    cmds.button(segm_button, edit=True, 
                command=partial(display_segmentation_callback, segm_button, state))
    scan_button = cmds.button(label='3D Scan', backgroundColor=[200 / 256, 225 / 256, 80 / 256])
    cmds.button(scan_button, edit=True, 
                command=partial(imitate_3D_scan_callback, scan_button, state))

    cmds.setParent('..')
    # separate
    cmds.separator()

    # Saving folder
    saving_to_field = text_button_group(saving_folder_callback, state, 
                                        label='Saving to: ', button_label='Choose')
    # saving requests
    equal_rowlayout(2, win_width=window_width, offset=main_offset)
    cmds.button(label='Save snapshot', backgroundColor=[227 / 256, 255 / 256, 119 / 256],
                command=partial(quick_save_callback, saving_to_field, state), 
                ann='Quick save with pattern spec and sim config')
    cmds.button(label='Save with render', backgroundColor=[255 / 256, 140 / 256, 73 / 256], 
                command=partial(full_save_callback, saving_to_field, state), 
                ann='Full save with pattern spec, sim config, garment mesh & rendering')
    cmds.setParent('..')

    # Last
    cmds.text(label='')    # offset

    # fin
    cmds.showWindow(win)


# ----- State -------
class State(object):
    def __init__(self):
        self.pattern_layout = None  # to be set on UI init
        self.garment = None
        self.scene = None
        self.save_to = None
        self.saving_prefix = None
        self.body_file = None
        self.config = customconfig.Properties()
        self.scenes_path = ''
        mymaya.simulation.init_sim_props(self.config)  # use default setup for simulation -- for now

    def reload_garment(self):
        """Reloads garment Geometry & UI with current scene. 
            JSON is NOT loaded from disk as it's on-demand operation"""
        if self.garment is None:
            return 

        if self.scene is not None:
            self.garment.load(
                shader_group=self.scene.cloth_SG(), 
                obstacles=[self.scene.body, self.scene.floor()], 
                config=self.config['sim']['config']
            )
        else:
            self.garment.load(config=self.config['sim']['config'])

        # calling UI after loading for correct connection of attributes
        self.garment.drawUI(self.pattern_layout)

    def fetch(self):
        """Update info in deendent object from Maya"""
        if self.scene is not None:
            self.scene.fetch_props_from_Maya()
        garment_conf = self.garment.fetchSimProps()
        self.config.set_section_config(
            'sim', 
            material=garment_conf['material'], 
            body_friction=garment_conf['body_friction'],
            collision_thickness=garment_conf['collision_thickness']
        )
    
    def serialize(self, directory):
        """Serialize text-like objects"""
        self.config.serialize(os.path.join(directory, 'sim_props.json'))
        self.garment.view_ids = True
        self.garment.serialize(directory, to_subfolder=False)

    def save_scene(self, directory):
        """Save scene objects"""
        self.garment.save_mesh(directory)
        self.scene.render(directory, self.garment.name)


# ------- Errors --------
class CustomError(Exception):
    def __init__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return(self.__class__.__name__ + ', {0} '.format(self.message))
        else:
            return(self.__class__.__name__)


class SceneSavingError(CustomError):
    def __init__(self, *args):
        super(SceneSavingError, self).__init__(*args)


# --------- UI Drawing ----------
def equal_rowlayout(num_columns, win_width, offset):
    """Create new layout with given number of columns + extra columns for spacing"""
    col_width = []
    for col in range(1, num_columns + 1):
        col_width.append((col, win_width / num_columns - offset))

    col_attach = [(col, 'both', offset) for col in range(1, num_columns + 1)]

    return cmds.rowLayout(
        numberOfColumns=num_columns,
        columnWidth=col_width, 
        columnAttach=col_attach, 
    )


def text_button_group(callback, state, label='', button_label='Click'):
    """Custom version of textFieldButtonGrp"""
    cmds.rowLayout(nc=3, adj=2)
    cmds.text(label=label)
    text_field = cmds.textField(editable=False)
    cmds.button(
        label=button_label, 
        bgc=[0.99, 0.66, 0.46],  # backgroundColor=[255 / 256, 169 / 256, 119 / 256], 
        command=partial(callback, text_field, state))
    cmds.setParent('..')
    return text_field


# ----- Callbacks -----
# -- Loading --
def sample_callback(text, *args):
    print('Called ' + text)
    

def template_field_callback(view_field, state, *args):
    """Get the file with pattern"""

    current_dir = os.path.dirname(cmds.textField(view_field, query=True, text=True))

    multipleFilters = "JSON (*.json);;All Files (*.*)"
    template_file = cmds.fileDialog2(
        fileFilter=multipleFilters, 
        dialogStyle=2, 
        fileMode=1, 
        caption='Choose pattern specification file',
        startingDirectory=current_dir
    )
    if not template_file:  # do nothing
        return
    template_file = template_file[0]

    cmds.textField(view_field, edit=True, text=template_file)

    # create new grament
    if state.garment is not None:
        state.garment.clean(delete=True)  # sometimes cleaning by garbage collector (gc) is late => call for clearning manually
        # TODO check what objects cause the late cleaning by checking references in gc

    state.garment = mymaya.MayaGarmentWithUI(template_file, True) 
    state.reload_garment()


def load_body_callback(view_field, state, *args):
    """Get body file & (re)init scene"""
    current_dir = os.path.dirname(cmds.textField(view_field, query=True, text=True))
    multipleFilters = "OBJ (*.obj);;All Files (*.*)"
    file = cmds.fileDialog2(
        fileFilter=multipleFilters, 
        dialogStyle=2, 
        fileMode=1, 
        caption='Choose body obj file',
        startingDirectory=current_dir
    )
    if not file:  # do nothing
        return 

    file = file[0]
    cmds.textField(view_field, edit=True, text=file)

    state.config['body'] = os.path.basename(file)  # update info
    state.body_file = file
    state.scene = mymaya.Scene(file, state.config['render'], scenes_path=state.scenes_path, clean_on_die=True)  # previous scene will autodelete
    state.reload_garment()
            

def load_props_callback(view_field, state, *args):
    """Load sim & renderign properties from file rather then use defaults"""
    current_dir = os.path.dirname(cmds.textField(view_field, query=True, text=True))
    multipleFilters = "JSON (*.json);;All Files (*.*)"
    file = cmds.fileDialog2(
        fileFilter=multipleFilters, 
        dialogStyle=2, 
        fileMode=1, 
        caption='Choose sim & rendering properties file',
        startingDirectory=current_dir
    )
    if not file:  # do nothing
        return

    file = file[0]
    cmds.textField(view_field, edit=True, text=file)
    
    # Edit the incoming config to reflect explicit choiced made in other UI elements
    in_config = customconfig.Properties(file)

    # Use current body info instead of one from config
    if state.body_file is not None:
        in_config['body'] = os.path.basename(state.body_file)

    # Use current scene info instead of one from config 
    if 'scene' not in state.config['render']['config']:  # remove entirely
        in_config['render']['config'].pop('scene', None)
    else:
        in_config['render']['config']['scene'] = state.config['render']['config']['scene']

    # After the adjustments made, apply the new config to all elements
    state.config = in_config
    mymaya.simulation.init_sim_props(state.config)  # fill the empty parts

    if state.scene is not None:
        state.scene = mymaya.Scene(
            state.body_file, state.config['render'], 
            scenes_path=state.scenes_path, clean_on_die=True)  
        
    if state.garment is not None:
        state.reload_garment()


def load_scene_callback(view_field, state, *args):
    """Load sim & renderign properties from file rather then use defaults"""
    current_dir = os.path.dirname(cmds.textField(view_field, query=True, text=True))
    multipleFilters = "MayaBinary (*.mb);;All Files (*.*)"
    file = cmds.fileDialog2(
        fileFilter=multipleFilters, 
        dialogStyle=2, 
        fileMode=1, 
        caption='Choose scene setup Maya file',
        startingDirectory=current_dir
    )
    if not file:  # do nothing
        return

    file = file[0]
    cmds.textField(view_field, edit=True, text=file)

    # Use current scene info instead of one from config
    state.config['render']['config']['scene'] = os.path.basename(file)
    state.scenes_path = os.path.dirname(file)

    # Update scene with new config
    if state.scene is not None:
        # del state.scene
        state.scene = mymaya.Scene(
            state.body_file, state.config['render'], 
            scenes_path=state.scenes_path,
            clean_on_die=True)  
        state.reload_garment()


def reload_garment_callback(state, *args):
    """
        (re)loads current garment object to Maya if it exists
    """
    if state.garment is not None:
        state.garment.reloadJSON()
        state.reload_garment()


# -- Operations --
def start_sim_callback(button, state, *args):
    """ Start simulation """
    if state.garment is None or state.scene is None:
        cmds.confirmDialog(title='Error', message='Load pattern specification & body info first')
        return
    print('Simulating..')

    # Reload geometry in case something changed
    state.reload_garment()

    mymaya.qualothwrapper.start_maya_sim(state.garment, state.config['sim'])

    # Update button 
    cmds.button(button, edit=True, 
                label='Stop Sim', backgroundColor=[245 / 256, 96 / 256, 66 / 256],
                command=partial(stop_sim_callback, button, state))


def stop_sim_callback(button, state, *args):
    """Stop simulation execution"""
    # toggle playback
    cmds.play(state=False)
    print('Simulation::Stopped')
    # uppdate button state
    cmds.button(button, edit=True, 
                label='Start Sim', backgroundColor=[227 / 256, 255 / 256, 119 / 256],
                command=partial(start_sim_callback, button, state))

    cmds.select(state.garment.get_qlcloth_props_obj())  # for props change


def check_collisions_callback(button, state, *args):
    """Run removal of faces that might be invisible to 3D scanner"""

    # indicate waiting for imitation finish
    cmds.button(button, edit=True, 
                label='Checking...', backgroundColor=[245 / 256, 96 / 256, 66 / 256],
                command=partial(stop_sim_callback, button, state))
    cmds.refresh(currentView=True)

    cmds.confirmDialog(
        title='Simulation quality info:', 
        message=(
            'Simulation quality checks: \n\n'
            'Garment intersect colliders: {} \n'
            'Garment has self-intersections: {}').format(
                'Yes' if state.garment.intersect_colliders_3D() else 'No', 
                'Yes' if state.garment.self_intersect_3D(verbose=True) else 'No'), 
        button=['Ok'], defaultButton='Ok', cancelButton='Ok', dismissString='Ok')

    cmds.button(button, edit=True, 
                label='Collisions', backgroundColor=[250 / 256, 200 / 256, 119 / 256],
                command=partial(check_collisions_callback, button, state))


def imitate_3D_scan_callback(button, state, *args):
    """Run removal of faces that might be invisible to 3D scanner"""

    # indicate waiting for imitation finish
    cmds.button(button, edit=True, 
                label='Scanning...', backgroundColor=[245 / 256, 96 / 256, 66 / 256])
    cmds.refresh(currentView=True)

    if 'scan_imitation' in state.config:
        num_rays = state.config['scan_imitation']['config']['test_rays_num']
        vis_rays = state.config['scan_imitation']['config']['visible_rays_num']
        mymaya.scan_imitation.remove_invisible(
            state.garment.get_qlcloth_geomentry(),
            [state.scene.body] if state.scene is not None else [], 
            num_rays, vis_rays
        )
    else:  # go with function defaults
        mymaya.scan_imitation.remove_invisible(
            state.garment.get_qlcloth_geomentry(),
            [state.scene.body] if state.scene is not None else []
        )

    cmds.button(button, edit=True, 
                label='3D Scan', backgroundColor=[200 / 256, 225 / 256, 80 / 256],
                command=partial(imitate_3D_scan_callback, button, state))


def display_segmentation_callback(button, state, *args):
    """
        Visualize the segmentation labels
    """
    print('Segmentation displayed!')
    # indicate waiting for imitation finish
    cmds.button(button, edit=True, 
                label='Segmenting...', backgroundColor=[245 / 256, 96 / 256, 66 / 256])
    cmds.refresh(currentView=True)

    state.garment.display_vertex_segmentation()

    cmds.button(button, edit=True, 
                label='Segmentation', backgroundColor=[150 / 256, 225 / 256, 80 / 256],
                command=partial(display_segmentation_callback, button, state))    


# -- Saving ---
def win_closed_callback(*args):
    """Clean-up"""
    # Remove solver objects from the scene
    cmds.delete(cmds.ls('qlSolver*'))
    # Other created objects will be automatically deleted through destructors


def saving_folder_callback(view_field, state, *args):
    """Choose folder to save files to"""

    current_dir = cmds.textField(view_field, query=True, text=True)

    directory = cmds.fileDialog2(
        dialogStyle=2, 
        fileMode=3,  # directories 
        caption='Choose folder to save snapshots and renderings to',
        startingDirectory=current_dir
    )
    if not directory:  # do nothing
        return 

    directory = directory[0]
    cmds.textField(view_field, edit=True, text=directory)

    state.save_to = directory

    # request saving prefix
    tag_result = cmds.promptDialog(
        t='Enter a saving prefix', 
        m='Enter a saving prefix:', 
        button=['OK', 'Cancel'],
        defaultButton='OK',
        cancelButton='Cancel',
        dismissString='Cancel'
    )
    if tag_result == 'OK':
        tag = cmds.promptDialog(query=True, text=True)
        state.saving_prefix = tag
    else:
        state.saving_prefix = None

    return True


def _new_dir(root_dir, tag='snap'):
    """create fresh directory for saving files"""
    folder = tag + '_' + datetime.now().strftime('%y%m%d-%H-%M-%S')
    path = os.path.join(root_dir, folder)
    os.makedirs(path)
    return path


def _create_saving_dir(view_field, state):
    """Create directory to save to """

    if state.garment is None:
        cmds.confirmDialog(title='Error', message='Load pattern specification first')
        raise SceneSavingError('Garment is not loaded before saving')
    
    if state.save_to is None:
        if not saving_folder_callback(view_field, state):
            raise SceneSavingError('Saving folder not supplied')
    
    if state.saving_prefix is not None:
        tag = state.saving_prefix
    else: 
        tag = state.garment.name

    new_dir = _new_dir(state.save_to, tag)

    return new_dir


def quick_save_callback(view_field, state, *args):
    """Quick save with pattern spec and sim config"""
    try: 
        new_dir = _create_saving_dir(view_field, state)
    except SceneSavingError: 
        return 

    state.fetch()
    state.serialize(new_dir)

    state.garment.save_mesh(new_dir)

    print('Garment info saved to ' + new_dir)


def full_save_callback(view_field, state, *args):
    """Full save with pattern spec, sim config, garment mesh & rendering"""

    if state.garment is None or state.scene is None:
        cmds.confirmDialog(title='Error', message='Load pattern specification & body info first')
        return

    # do the same as for quick save
    try: 
        new_dir = _create_saving_dir(view_field, state)
    except SceneSavingError: 
        return 

    # save scene objects
    state.save_scene(new_dir)

    # save text properties
    state.fetch()
    state.serialize(new_dir)

    print('Pattern spec, props, 3D mesh & render saved to ' + new_dir)

    cmds.select(state.garment.get_qlcloth_props_obj())  # for props change
