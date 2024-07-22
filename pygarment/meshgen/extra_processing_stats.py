from pathlib import Path
from customconfig import Properties



system_config = Properties('./system.json')
dataset = 'test_no_drag_100_240209-16-27-32'  # 'test_drag_100_240209-16-27-32'
body_type = 'default_body'  # 'random_body' # 'default_body'

dataprop_file = Path(system_config['output']) / dataset / body_type / f'dataset_properties_{body_type}.yaml'
props = Properties(dataprop_file)

fails = props['sim']['stats']['fails']
filter_fails = (
    # fails['simulation_timeout'] +
    fails['meshgen-timeout']
    + fails['gt_edges_creation']
    + fails['multi_stitching']
    + fails['pattern_loading']
    + fails['static_equilibrium']
    + fails['crashes']
)


# Self-intersection_stats
self_stats = props['sim']['stats']['self_collisions']
filtered_self = {k:v for k, v in self_stats.items() if k not in filter_fails}
print('Self-collisions')
print(filtered_self)


# Body-intersection_stats
body_stats = props['sim']['stats']['body_collisions']
filtered_body = {k:v for k, v in self_stats.items() if k not in filter_fails}
print('Body collisions')
print(filtered_body)