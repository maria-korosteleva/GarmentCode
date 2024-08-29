"""
    The module contain Porperties class to manage paramters & stats in various parts of the system
"""

from datetime import timedelta
import json
import yaml
from numbers import Number
import traceback
import sys
from pathlib import Path
import numpy as np

# for system info
import platform
import psutil

# --- Nice dumping of floats ---
def float_representer(dumper, data):

    if data != data or (data == 0.0 and data == 1.0):
        value = '.nan'
    elif data == dumper.inf_value:
        value = '.inf'
    elif data == -dumper.inf_value:
        value = '-.inf'
    else:
        # Custom representation: 
        # https://stackoverflow.com/a/33944926
        value = f'{data:.3g}'
        if '.' not in value or 'e' in value:   # e only appears for large int numbers with this precision
            # An integer hidden as a float
            value = f'{int(data):d}.0'

    return dumper.represent_scalar('tag:yaml.org,2002:float', value)
yaml.add_representer(float, float_representer)


# --- Main class ----
class Properties():
    """Keeps, loads, and saves cofiguration & statistic information
        Supports gets&sets as a dictionary
        Provides shortcuts for batch-init configurations

        One of the usages -- store system-dependent basic cofiguration
    """
    def __init__(self, filename="", clean_stats=False):
        self.properties = {}
        self.properties_on_load = {}

        if filename:
            self.properties = self._from_file(filename)
            self.properties_on_load = self._from_file(filename)
            if clean_stats:  # only makes sense when initialized from file =) 
                self.clean_stats(self.properties)

    # ---- Base utils ----
    def has(self, key):
        """Used to query if a top-level property/section is already defined"""
        return key in self.properties

    def serialize(self, filename, backup=None):
        """Log current props to file. If logging failed, at least restore
        provided backup or originally loaded props
            * backup is expected to be a Properties object
        """
        try:
            extention = Path(filename).suffix.lower()
            if extention == '.json':
                with open(filename, 'w') as f_json:
                    json.dump(self.properties, f_json, indent=2, sort_keys=True)
            elif extention == '.yaml':
                with open(filename, 'w') as f:
                    yaml.dump(
                        self.properties, 
                        f,
                        default_flow_style=False,
                        sort_keys=False
                    )
            else:
                raise ValueError(f'{self.__class__.__name__}::ERROR::Unsupported file type on serialization: {extention}')
            
        except Exception as e:
            print('Exception occured while saving properties:')
            traceback.print_exception(*sys.exc_info()) 
            # save backup, s.t. the data is not lost due to interruption of
            # the file override

            if backup is not None: 
                backup.serialize(filename)
            else:
                with open(filename, 'w') as f_json:
                    json.dump(self.properties_on_load, f_json,
                              indent=2, sort_keys=True)
            raise RuntimeError('Error occured while saving properties. Backup version is saved instead')

    def merge(self, filename="", clean_stats=False, re_write=True,
              adding_tag='added'):
        """Merge current set of properties with the one from file
            * re_write=True sets the default merging of Python dicts, values
            from new props overrite
                the one from old one if keys are the same
            * re_write=False will keep both properties if their values are
            different (imported one marked with adding_tag)
        """
        new_props = self._from_file(filename)
        if clean_stats:
            self.clean_stats(new_props)
        # merge
        self._recursive_dict_update(self.properties, new_props, re_write, adding_tag)

    # --- Specialised utils (require domain knowledge) --

    def is_fail(self, dataname):
        """
            Check if a particular object is listed as fail in any of the sections
            Fails may be listed in the stats subsection of any of the section
        """
        _, fails_list = self.count_fails()

        return dataname in fails_list

    def is_fail_section(self, dataname):
        """
            Check if a particular object is listed as fail in any of the sections
            Fails may be listed in the stats subsection of any of the section
            return the section name
        """

        for section_key in self.properties:
            section = self.properties[section_key]
            if isinstance(section, dict) and 'stats' in section and ('fails' in section['stats']):
                if isinstance(section['stats']['fails'], dict):
                    for key in section['stats']['fails']:
                        if not isinstance(section['stats']['fails'][key], list):
                            raise NotImplementedError(
                                'Properties::ERROR:: Fails subsections of the type {} is not supported'.format(
                                    type(section['stats']['fails'][key])))
                                    
                        if dataname in section['stats']['fails'][key]:  # expects a list as value
                            return True, key

                elif isinstance(section['stats']['fails'], list):
                    if dataname in section['stats']['fails'][key]:  # expects a list as value
                        return True, 'fails'
                else:
                    raise NotImplementedError('Properties::ERROR:: Fails subsections of the type {} is not supported'.format(type(section['stats']['fails'])))

        return False, None

    def count_fails(self, log=False):
        """
            Number of (unique) datapoints marked as fail
        """
        fails = []
        for section_key in self.properties:
            section = self.properties[section_key]
            section_fails = []
            if isinstance(section, dict) and 'stats' in section and ('fails' in section['stats']):
                if isinstance(section['stats']['fails'], dict):
                    for key in section['stats']['fails']:
                        if not isinstance(section['stats']['fails'][key], list):
                            raise NotImplementedError(
                                'Properties::ERROR:: Fails subsections of the type {} is not supported'.format(
                                    type(section['stats']['fails'][key])))
                                    
                        section_fails += section['stats']['fails'][key] # expects a list as value

                elif isinstance(section['stats']['fails'], list):
                    section_fails += section['stats']['fails']
                else:
                    raise NotImplementedError('Properties::Error:: Fails subsections of the type {} is not supported'.format(type(section['stats']['fails'])))

                if log:
                    section['stats']['fails_count'] = len(list(set(section_fails)))

                fails += section_fails

        fails = list(set(fails))

        return len(fails), fails

    def add_fail(self, section_name, fail_type, info):
        """Write a failure case to a requested section's stats"""

        section = self.properties[section_name]
        if 'fails' not in section['stats']:
            section['stats']['fails'] = {}
        try:
            section['stats']['fails'][fail_type].append(info)
        except KeyError:
            section['stats']['fails'][fail_type] = [info]
            

    # ---------- Properties updates ---------------
    def set_basic(self, **kwconfig):
        """Adds/updates info on the top level of properties
            Only to be used for basic information!
        """
        # section exists
        for key, value in kwconfig.items():
            self.properties[key] = value

    def set_section_config(self, section, **kwconfig):
        """adds or modifies a (top level) section and updates its configuration info
        """
        # create new section
        if section not in self.properties:
            self.properties[section] = {
                'config': kwconfig,
                'stats': {}
            }
            return
        # section exists
        for key, value in kwconfig.items():
            self.properties[section]['config'][key] = value

    def set_section_stats(self, section, **kwstats):
        """adds or modifies a (top level) section and updates its statistical info
        """
        # create new section
        if section not in self.properties:
            self.properties[section] = {
                'config': {},
                'stats': kwstats
            }
            return
        # section exists
        for key, value in kwstats.items():
            self.properties[section]['stats'][key] = value

    def clean_stats(self, properties):
        """ Remove info from all Stats sub sections """
        for _, value in properties.items():
            # detect section
            if isinstance(value, dict) and 'stats' in value:
                value['stats'] = {}

    def summarize_stats(self, 
                        key, 
                        log_sum=False, log_avg=False, 
                        log_median=False, log_80=False, log_95=False,
                        log_min=False, log_max=False,
                        as_time=False):
        """Make a summary of requested key with requested statistics in current props"""
        updated = False
        for section in self.properties.values():
            # check all stats sections
            if isinstance(section, dict) and 'stats' in section:
                if key in section['stats']:
                    stats_values = section['stats'][key]
                    if isinstance(stats_values, dict):
                        stats_values = list(stats_values.values())

                    # summarize all foundable statistics
                    if isinstance(stats_values, list) and len(stats_values) > 0 and isinstance(stats_values[0], Number):
                        if log_sum:
                            section['stats'][key + "_sum"] = str(timedelta(seconds=sum(stats_values))) if as_time else sum(stats_values)
                            updated = True
                        if log_avg:
                            section['stats'][key + "_avg"] = sum(stats_values) / len(stats_values)
                            if as_time:
                                section['stats'][key + "_avg"] = str(timedelta(seconds=section['stats'][key + "_avg"]))
                            updated = True
                        if log_median:
                            section['stats'][key + "_med"] = str(timedelta(seconds=np.percentile(stats_values, 50))) if as_time else float(np.percentile(stats_values, 50))
                            updated = True
                        if log_80:
                            section['stats'][key + "_p80"] = str(timedelta(seconds=np.percentile(stats_values, 80))) if as_time else float(np.percentile(stats_values, 80))
                            updated = True
                        if log_95:
                            section['stats'][key + "_p95"] = str(timedelta(seconds=np.percentile(stats_values, 95))) if as_time else float(np.percentile(stats_values, 95))
                            updated = True
                        if log_min:
                            section['stats'][key + "_min"] = str(timedelta(seconds=min(stats_values))) if as_time else min(stats_values)
                            updated = True
                        if log_max:
                            section['stats'][key + "_max"] = str(timedelta(seconds=max(stats_values))) if as_time else max(stats_values)
                            updated = True
        return updated

    # -- Specialised updates (require domain knowledge) --
    def add_sys_info(self):
        """Add or update system information on the top level of config"""

        if sys.version_info.major < 3:
            raise NotImplementedError('{}::Requesting system info is not supported for Python 2'.format(self.__class__.__name__))

        # https://stackoverflow.com/questions/3103178/how-to-get-the-system-info-with-python

        self.properties['system_info'] = {}

        self.properties['system_info']['platform'] = platform.system()
        self.properties['system_info']['platform-release'] = platform.release()
        self.properties['system_info']['platform-version'] = platform.version()
        self.properties['system_info']['architecture'] = platform.machine()
        self.properties['system_info']['processor'] = platform.processor()
        self.properties['system_info']['ram'] = str(round(psutil.virtual_memory().total / (1024.0 ** 3))) + " GB"

        try: 
            import warp   # Optional section
            if warp.context.runtime is None:
                # runtime = warp.context.Runtime()
                warp.init()
            else:
                print(f'{self.__class__.__name__}::INFO::Saving GPU info -- warp already initialized')
            curr_device = warp.get_device()   
            self.properties['system_info']['GPU'] = curr_device.name if curr_device.is_cuda else 'Not used'
        except ImportError:
            pass  # Don't do anything if warp not available

    def stats_summary(self):
        """
            Compute data simulation processing statistics
        """
        updated_render = self.summarize_stats('render_time', log_sum=True, log_avg=True, as_time=True)
        updated_frames = self.summarize_stats('fin_frame', log_avg=True)
        updated_sim_time = self.summarize_stats('sim_time', log_sum=True, log_avg=True, as_time=True)
        updated_spf = self.summarize_stats('spf', log_avg=True, as_time=True)
        updated_scan = self.summarize_stats('processing_time', log_sum=True, log_avg=True, as_time=True)
        updated_scan_faces = self.summarize_stats('faces_removed', log_avg=True)

        updated_self_collisions = self.summarize_stats(
            'self_collisions', log_avg=True, log_median=True, log_80=True, log_95=True)
        updated_body_collisions = self.summarize_stats(
            'body_collisions', log_avg=True, log_median=True, log_80=True, log_95=True)
        
        updated_face_count = self.summarize_stats(
            'face_count', log_avg=True, log_median=True, log_min=True, log_max=True)
        updated_panel_count = self.summarize_stats(
            'panel_count', log_avg=True, log_median=True, log_min=True, log_max=True)
 
        # fails
        self.count_fails(log=True)

        if not (updated_frames and updated_render and updated_sim_time and updated_spf and updated_self_collisions and updated_body_collisions):
            print(f'{self.__class__.__name__}::WARNING::Sim stats summary '
                  'requested, but not all sections were updated')

    # ---- Private utils ----
    def _from_file(self, filename):
        """ Load properties from previously created file """
        extention = Path(filename).suffix.lower()
        if extention == '.json':
            with open(filename, 'r') as f_json:
                return json.load(f_json)
        elif extention == '.yaml':
            with open(filename, 'r') as f:
                return yaml.safe_load(f)
        else:
            raise ValueError(f'{self.__class__.__name__}::ERROR::Unsupported file type on load: {extention}')


    def _recursive_dict_update(self, in_dict, new_dict, re_write=True, adding_tag='added', in_stats=False):
        """
            updates input dictionary with the update_dict properly updating all the inner dictionaries
            re_write = True replaces the values with the ones from new dictionary if they happen to be different, 
            re_write = False extends dictionary to include both values if different 

            "in_stats" shows if we are currently in any of the stats subsections. 
                In this case, lists are merged instead of being re-written
        """
        if not isinstance(new_dict, dict):
            in_dict = new_dict  # just update with all values
            return

        for new_key in new_dict:
            if new_key in in_dict and isinstance(in_dict[new_key], dict):
                # update inner dict properly
                self._recursive_dict_update(
                    in_dict[new_key], new_dict[new_key], 
                    re_write, adding_tag, 
                    (in_stats or new_key == 'stats'))
            elif not re_write and new_key in in_dict and in_dict[new_key] != new_dict[new_key]:
                if in_stats and isinstance(in_dict[new_key], list):
                    # merge lists inside stats sections
                    in_dict[new_key] = in_dict[new_key] + new_dict[new_key]
                else:
                    # Keep both versions (e.g. in configs)
                    adding_name = new_key + '_' + adding_tag
                    while adding_name in in_dict:   # in case even the added version is already there
                        adding_name = adding_name + '_added'

                    in_dict[adding_name] = new_dict[new_key]  
                    in_dict[new_key + '_' + self['name']] = in_dict[new_key]
            else:  # at sertain depth there will be no more dicts -- recusrion stops
                in_dict[new_key] = new_dict[new_key]
        # if new_dict is empty -- no update happens

    def __getitem__(self, key):
        return self.properties[key]

    def __setitem__(self, key, value):
        self.properties[key] = value

    def __contains__(self, key):
        return key in self.properties

    def __str__(self):
        return str(self.properties)
