"""
    Run or Resume simulation of a pattern dataset with MayaPy standalone mode
    Note that this module is executed in Maya (or by mayapy)

    How to use: 
        * fill out system.json with approppriate paths 
        Running itself:
        ./datasim.py --data <dataset folder name> --minibatch <size>  --config <simulation_rendering_configuration.json>

"""
import argparse
import sys
import shutil
from pathlib import Path

# My modules
import pygarment.data_config as data_config
import pygarment.meshgen.datasim_utils as sim


def get_command_args():
    """command line arguments to control the run"""
    # https://stackoverflow.com/questions/40001892/reading-named-command-arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', '-d', help='name of dataset folder', type=str)
    parser.add_argument('--config', '-c', help='name of .json file with desired simulation&rendering config', type=str,
                        default=None)
    parser.add_argument('--minibatch', '-b', help='number of examples to simulate in this run', type=int, default=None)
    parser.add_argument('--default_body', action='store_true', help='run dataset on default body')
    parser.add_argument('--caching', action='store_true', help='cache intermediate simulation')
    parser.add_argument('--rewrite_config', action='store_true', help='cache intermediate simulation')

    args = parser.parse_args()
    print(args)

    return args

def gather_renders(out_data_path: Path, verbose=False):
    renders_path = out_data_path / 'renders'
    renders_path.mkdir(exist_ok=True)

    render_files = list(out_data_path.glob('**/*render*.png'))
    for file in render_files:
        try: 
            shutil.copy(str(file), str(renders_path))
        except shutil.SameFileError:
            if verbose:
                print(f'File {file} already exists')
            pass


if __name__ == "__main__":

    command_args = get_command_args()
    system_config = data_config.Properties('./system.json') 

    # ------ Dataset ------
    dataset = command_args.data
    datapath = Path(system_config['datasets_path']) / dataset
    init_dataset_file = datapath / 'dataset_properties.yaml'

    # Create dataset_file in correct folder (default_body or random_body)
    body_type = 'default_body' if command_args.default_body else 'random_body'
    datapath = datapath / body_type / 'data' # Overwrite datapath to specific body type

    output_path = Path(system_config['datasets_sim']) / dataset / body_type
    output_path.mkdir(parents=True, exist_ok=True) 
    dataset_file_body = output_path / f'dataset_properties_{body_type}.yaml'
    if not dataset_file_body.exists():
        shutil.copy(str(init_dataset_file), str(dataset_file_body))
    dataset_file = dataset_file_body

    props = data_config.Properties(dataset_file_body)
    if 'frozen' in props and props['frozen']: #Where is this set?
        # avoid accidential re-runs of data
        print('Warning: dataset is frozen, processing is skipped')
        sys.exit(0)

    # ------- Defining sim props -----
    props.set_basic(data_folder=dataset)  # in case data properties are from other dataset/folder, update info
    if command_args.config is not None:
        props.merge(
            Path(system_config['sim_configs_path']) / command_args.config, 
            re_write=command_args.rewrite_config)    # Re-write sim config only explicitly 

    # ----- Main loop ----------
    finished = sim.batch_sim(
        datapath, 
        output_path, 
        props,
        run_default_body=command_args.default_body,
        num_samples=command_args.minibatch,  # run in mini-batch if requested
        caching=command_args.caching, force_restart=False)

    # ----- Try and resim fails once -----
    if finished:
        # NOTE: Could be larger than a regular batch
        finished = sim.resim_fails(
            datapath, 
            output_path, 
            props,
            run_default_body=command_args.default_body,
            caching=command_args.caching)

    props.add_sys_info()   # Save system information
    props.serialize(dataset_file)

    # ------ Gather renders -------
    gather_renders(output_path)

    # -------- fin --------
    if finished:
        # finished processing the dataset
        print('Dataset processing finished')
        sys.exit(0)
    else:
        sys.exit(1)  # not finished dataset processing