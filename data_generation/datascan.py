"""
    Emulate the result of scanning a garment on existing dataset of simulated garments

    Support resuming functionality by default -- if you run on the dataset that already has some of the outputs,
     the datapoints will be skipped rather then re-evaluated
    
    IMPORTANT!! This script need to be run with mayapy to get access to Autodesk Maya Python API. 
        E.g., on Windows the command could look like this: 
        d:/Autodesk/Maya2020/bin/mayapy.exe "./data_generation/datascan.py"
    """

import os
import time
from datetime import timedelta
from importlib import reload

# Maya
from maya import cmds
import maya.standalone 	

# My modules
import customconfig
# reload in case we are in Maya internal python environment
reload(customconfig)


# Had to make copy of functions from datasim.py, becuase of issues with importing maya-related packages
def init_mayapy():
    try: 
        print('Initilializing Maya tools...')
        maya.standalone.initialize()
        print('Load plugins')
        cmds.loadPlugin('mtoa.mll')  # https://stackoverflow.com/questions/50422566/how-to-register-arnold-render
        cmds.loadPlugin('objExport.mll')  # same as in https://forums.autodesk.com/t5/maya-programming/invalid-file-type-specified-atomimport/td-p/9121166
        
    except Exception as e: 
        print(e)
        print('Init failed')
        pass


def stop_mayapy():  
    maya.standalone.uninitialize() 
    print("Maya stopped")


def transfer_segm_labels(verts_before, mesh, dir_path, name):
    """
        Save segmentation labels for mesh after scan imitation
    """
    verts_after = utils.get_vertices_np(mesh)
    verts_mapping = utils.match_vert_lists(verts_after, verts_before)

    # print(os.path.join(dir_path, name + '_sim_segmentation.txt'))

    with open(os.path.join(dir_path, name + '_sim_segmentation.txt'), 'r') as f:
        vert_labels = [line.rstrip() for line in f]  # remove \n
    scan_labels = [vert_labels[i] for i in verts_mapping]

    filepath = os.path.join(dir_path, name + '_scan_imitation_segmentation.txt')
    with open(filepath, 'w') as f:
        for panel_name in scan_labels:
            f.write("%s\n" % panel_name)
    return 0


if __name__ == "__main__":

    system_config = customconfig.Properties('system.json')  # Make sure it's in \Autodesk\MayaNNNN\
    path = system_config['templates_path']

    # ------ Datasets ------
    dataset_folders = [
        # 'merged_dress_sleeveless_2550_210429-13-12-52',
        # 'merged_jumpsuit_sleeveless_2000_210429-11-46-14',
        # 'merged_skirt_8_panels_1000_210521-16-20-14',
        # 'merged_wb_pants_straight_1500_210521-16-30-57',
        # 'merged_skirt_2_panels_1200_210521-16-46-27',
        # 'merged_jacket_2200_210521-16-55-26',
        # 'merged_tee_sleeveless_1800_210521-17-10-22',
        'merged_wb_dress_sleeveless_2600_210521-17-26-08',  # had fails
        # 'merged_jacket_hood_2700_210521-17-47-44',
        # 'data_1000_pants_straight_sides_210520-22-34-57'
    ]

    # ------ Start Maya instance ------
    init_mayapy()
    import mayaqltools as mymaya  # has to import after maya is loaded
    reload(mymaya)  # reload in case we are in Maya internal python environment
    from mayaqltools import utils

    for dataset in dataset_folders:
        datapath = os.path.join(system_config['datasets_path'], dataset)
        # print(datapath)
        dataset_file = os.path.join(datapath, 'dataset_properties.json')
        data_props = customconfig.Properties(dataset_file)
        if not data_props['to_subfolders']:
            raise NotImplementedError('Scanning only works on datasets organized in subfolders')  # just for simplicity 

        # load body to the scene
        body = utils.load_file(os.path.join(system_config['bodies_path'], data_props['body']), 'body')
        utils.scale_to_cm(body)

        # ------ Main loop --------
        if 'scan_imitation' not in data_props:
            number_of_rays = 30
            number_of_visible_rays = 4
            data_props.set_section_config(
                'scan_imitation', test_rays_num=number_of_rays, visible_rays_num=number_of_visible_rays)
            data_props.set_section_stats('scan_imitation', fails=[], faces_removed={}, processing_time={})
        if 'fails' not in data_props['scan_imitation']['stats']:
            data_props['scan_imitation']['stats']['fails'] = []
        if 'faces_removed' not in data_props['scan_imitation']['stats']:
            data_props['scan_imitation']['stats']['faces_removed'] = {}
        if 'processing_time' not in data_props['scan_imitation']['stats']:
            data_props['scan_imitation']['stats']['processing_time'] = {}
        if 'frozen' not in data_props:
            data_props['frozen'] = True   # when True, the files that are already processed will be skipped!
        
        
        # go over the examples in the data
        start_time = time.time()
        to_ignore = ['renders']  # special dirs not to include in the pattern list
        root, dirs, files = next(os.walk(datapath))  

        for name in dirs:
            if name not in to_ignore:
                dir_path = os.path.join(root, name)

                # skip if already has a corresponding file
                _, elem_dirs, elem_files = next(os.walk(dir_path))
                if data_props['frozen'] and any(['scan_imitation.obj' in filename for filename in elem_files]):
                    print('Datascan::Info::Skipped {} as already processed'.format(name))
                    continue
                    # unfreeze dataset to re-do scan imitation on already processed elements
                
                if not any([name + '_sim.obj' in filename for filename in elem_files]):
                    # simulation result does not exist
                    print('Datascan::Warning::Skipped {} as .obj file does not exist'.format(name))
                    data_props['scan_imitation']['stats']['fails'].append(name)
                    continue
                
                # load mesh
                garment = utils.load_file(os.path.join(dir_path, name + '_sim.obj'), name + '_sim')

                mesh, _ = utils.get_mesh_dag(garment)
                verts_before = utils.get_vertices_np(mesh)
                
                # do what we are here for
                removed, time_taken = mymaya.scan_imitation.remove_invisible(
                    garment, [body],
                    data_props['scan_imitation']['config']['test_rays_num'], 
                    data_props['scan_imitation']['config']['visible_rays_num'])
                data_props['scan_imitation']['stats']['faces_removed'][name] = removed
                data_props['scan_imitation']['stats']['processing_time'][name] = time_taken

                # save to original folder
                utils.save_mesh(garment, os.path.join(dir_path, name + '_scan_imitation.obj'))

                # transfer the segmentation labels 
                if not any([name + '_sim_segmentation.txt' in filename for filename in elem_files]):
                    # segmentation labels file for sim does not exist
                    print('Datascan::Warning::{}:: Skipped segmentation transfer as segmentation file does not exist'.format(name))
                    data_props['scan_imitation']['stats']['fails'].append(name)
                else:
                    try:
                        transfer_segm_labels(verts_before, mesh, dir_path, name)
                    except ValueError as e:
                        print(e)
                        data_props['scan_imitation']['stats']['fails'].append(name)

                data_props.serialize(dataset_file)  # just in case                
                cmds.delete(garment)  # cleanup

        # update props & save
        passed = time.time() - start_time
        data_props.summarize_stats('processing_time', log_sum=True, log_avg=True, as_time=True)
        data_props.summarize_stats('faces_removed', log_avg=True)
        data_props.set_section_stats(
            'scan_imitation', total_processing_time=str(timedelta(seconds=passed))
        )
        data_props['frozen'] = True  # force freezing after processing is finished
        
        data_props.serialize(dataset_file)

        # print('Scan imitation on {} performed successfully!!!'.format(dataset))

        # clean the scene s.t. next dataset can use another body mesh
        cmds.delete(body)

    # End Maya instance
    stop_mayapy()  # ensures correct exit without errors