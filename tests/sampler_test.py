import unittest
from pathlib import Path
from external.customconfig import Properties
from garment_sampler import generate, gather_visuals


def sample_data():
    system_props = Properties('../system.json')

    new = True
    if new:
        props = Properties()
        props.set_basic(
            design_file='../assets/design_params/default.yaml',
            body_file='../assets/body_measurments/f_smpl_avg.yaml',
            name='data_30',
            size=30,
            to_subfolders=True)
        props.set_section_config('generator')
    else:
        props = Properties(
            Path(system_props['datasets_path']) /
            'data_30_230802-12-25-09/dataset_properties.yaml', True)

    props['data_folder'] = system_props['data_folder'] + "/sampled/"
    generate(system_props['datasets_path'], props, verbose=False)
    gather_visuals(
        Path(system_props['datasets_path']) / props['data_folder'])
    print('Data generation completed!')


class RandomSamplerTest(unittest.TestCase):
    def test_sampler(self):
        for _ in range(1000):
            sample_data()


if __name__ == '__main__':
    unittest.main()
