"""Path configuration for simulation inputs and outputs."""

from pathlib import Path
from typing import Optional
import yaml
from datetime import datetime

class PathCofig:
    """
    Routines for getting paths to various relevant objects with standard names.
    
    This class manages all file paths for simulation inputs and outputs, including
    body meshes, garment specifications, simulation results, and rendered images.
    
    Attributes
    ----------
    _system : Properties
        System configuration properties
    _body_name : str
        Name of the body mesh to use
    _samples_folder_name : str
        Name of the samples folder (if using body sampling)
    _use_default_body : bool
        Whether to use default body or sampled body
    use_smpl_seg : bool
        Whether to use SMPL segmentation instead of default
    in_tag : str
        Input tag/name for the garment
    out_folder_tag : str
        Output folder tag (may include timestamp)
    sim_tag : str
        Simulation tag/name
    boxmesh_tag : str
        Boxmesh tag/name
    input : Path
        Input element path
    out : Path
        Output path (dataset level)
    out_el : Path
        Output element path (specific to this garment)
    bodies_path : Path
        Path to bodies directory
    in_body_mes : Path
        Path to body measurements YAML file
    in_body_obj : Path
        Path to body OBJ mesh file
    in_g_spec : Path
        Path to garment specification JSON file
    body_seg : Path
        Path to body segmentation JSON file
    in_design_params : Path
        Path to design parameters YAML file
    g_box_mesh : Path
        Path to boxmesh OBJ file
    g_box_mesh_compressed : Path
        Path to compressed boxmesh PLY file
    g_mesh_segmentation : Path
        Path to mesh segmentation text file
    g_orig_edge_len : Path
        Path to original edge lengths pickle file
    g_vert_labels : Path
        Path to vertex labels YAML file
    g_texture_fabric : Path
        Path to fabric texture PNG file
    g_texture : Path
        Path to texture PNG file
    g_mtl : Path
        Path to material MTL file
    g_specs : Path
        Path to garment specifications JSON file (copy)
    element_sim_props : Path
        Path to simulation properties YAML file
    body_mes : Path
        Path to body measurements YAML file (copy)
    design_params : Path
        Path to design parameters YAML file (copy)
    g_sim : Path
        Path to simulated garment OBJ file
    g_sim_glb : Path
        Path to simulated garment GLB file
    g_sim_compressed : Path
        Path to compressed simulated garment PLY file
    usd : Path
        Path to USD simulation file
    """
    
    # Class variable type annotations
    _bodies_default_path: Path
    _body_samples_path: Path | None
    _body_name: str
    _samples_folder_name: str
    _use_default_body: bool
    use_smpl_seg: bool
    in_tag: str
    out_folder_tag: str
    sim_tag: str
    boxmesh_tag: str
    input: Path
    out: Path
    out_el: Path
    bodies_path: Path
    in_body_mes: Path
    in_body_obj: Path
    in_g_spec: Path
    body_seg: Path
    in_design_params: Path
    g_box_mesh: Path
    g_box_mesh_compressed: Path
    g_mesh_segmentation: Path
    g_orig_edge_len: Path
    g_vert_labels: Path
    g_texture_fabric: Path
    g_texture: Path
    g_mtl: Path
    g_specs: Path
    element_sim_props: Path
    body_mes: Path
    design_params: Path
    g_sim: Path
    g_sim_glb: Path
    g_sim_compressed: Path
    usd: Path
    
    def __init__(self, 
                 in_element_path: str | Path, 
                 out_path: str | Path, 
                 in_name: str, 
                 out_name: Optional[str] = None, 
                 body_name: str = '', 
                 samples_name: str = '', 
                 default_body: bool = True,
                 smpl_body: bool = False,
                 add_timestamp: bool = False,
                 bodies_default_path: str | Path | None = None,
                 body_samples_path: str | Path | None = None) -> None:
        """
        Initialize path configuration for simulation inputs and outputs.
        
        Parameters
        ----------
        in_element_path : str | Path
            Path to input element directory
        out_path : str | Path
            Dataset level output path
        in_name : str
            Input name/tag for the garment
        out_name : Optional[str], optional
            Output name/tag (defaults to in_name if None)
        body_name : str, optional
            Name of default body to use (default: '')
        samples_name : str, optional
            Name of samples folder for body sampling (default: '')
        default_body : bool, optional
            Whether to use default body (True) or sampled body (False) (default: True)
        smpl_body : bool, optional
            Whether to use SMPL segmentation (default: False)
        add_timestamp : bool, optional
            Whether to add timestamp to output folder name (default: False)
        bodies_default_path : str | Path | None, optional
            Path to default bodies directory. If None, will try to read from system.json (backward compatibility)
        body_samples_path : str | Path | None, optional
            Path to body samples directory. If None, will try to read from system.json (backward compatibility)
        """
        # Set system paths - accept as parameters or fall back to Properties for backward compatibility
        self._bodies_default_path = Path(bodies_default_path)
        self._body_samples_path = Path(body_samples_path) if body_samples_path is not None else body_samples_path
        
        self._body_name = body_name
        self._samples_folder_name = samples_name
        self._use_default_body = default_body
        self.use_smpl_seg = smpl_body

        # Tags
        if out_name is None:
            out_name = in_name
        self.in_tag = in_name
        self.out_folder_tag = f'{out_name}_{datetime.now().strftime("%y%m%d-%H-%M-%S")}' if add_timestamp else out_name
        self.sim_tag = out_name 
        self.boxmesh_tag = out_name

        # Base paths
        self.input = Path(in_element_path)
        self.out = Path(out_path)
        self.out_el = Path(out_path) / self.out_folder_tag
        self.out_el.mkdir(parents=True, exist_ok=True)
        
        # Individual file paths
        self._update_in_paths()
        self._update_boxmesh_paths()
        self.update_in_copies_paths()
        self.update_sim_paths()
    
    def _update_in_paths(self) -> None:
        """
        Update input paths based on body type and configuration.
        
        Determines paths for body meshes, measurements, specifications, and
        segmentation files based on whether using default or sampled bodies.
        """
        # Base path
        if not self._samples_folder_name or self._use_default_body:
            self.bodies_path = self._bodies_default_path
        else:
            if self._body_samples_path is None:
                raise ValueError("body_samples_path must be provided when using sampled bodies")
            self.bodies_path = self._body_samples_path / self._samples_folder_name / 'meshes'

        # Body measurements
        if not self._samples_folder_name:
            self.in_body_mes = self.bodies_path / f'{self._body_name}.yaml'
        else:
            self.in_body_mes = self.input / 'body_measurements.yaml'
        
        with open(self.in_body_mes, 'r') as file:
            body_dict = yaml.load(file, Loader=yaml.SafeLoader)
        if 'body_sample' in body_dict['body']:   # Not present in default measurements
            self._body_name = body_dict['body']['body_sample']

        self.in_body_obj = self.bodies_path / f'{self._body_name}.obj'
        self.in_g_spec = self.input / f'{self.in_tag}_specification.json'
        self.body_seg = self._bodies_default_path / ('ggg_body_segmentation.json' if not self.use_smpl_seg else 'smplx_vert_segmentation.json')
        self.in_design_params = self.input / 'design_params.yaml'

    def _update_boxmesh_paths(self) -> None:
        """
        Update boxmesh output paths.
        
        Sets paths for boxmesh OBJ, compressed PLY, segmentation, edge lengths,
        vertex labels, textures, and material files.
        """
        self.g_box_mesh = self.out_el / f'{self.boxmesh_tag}_boxmesh.obj'
        self.g_box_mesh_compressed = self.out_el / f'{self.boxmesh_tag}_boxmesh.ply'
        self.g_mesh_segmentation = self.out_el / f'{self.boxmesh_tag}_sim_segmentation.txt'
        self.g_orig_edge_len = self.out_el / f'{self.boxmesh_tag}_orig_lens.pickle'
        self.g_vert_labels = self.out_el / f'{self.boxmesh_tag}_vertex_labels.yaml'
        self.g_texture_fabric = self.out_el / f'{self.boxmesh_tag}_texture_fabric.png'
        self.g_texture = self.out_el / f'{self.boxmesh_tag}_texture.png'
        self.g_mtl = self.out_el / f'{self.boxmesh_tag}_material.mtl'
        
    def update_in_copies_paths(self) -> None:
        """
        Update paths for input file copies in output directory.
        
        Sets paths for copies of specifications, simulation properties,
        body measurements, and design parameters in the output directory.
        """
        self.g_specs = self.out_el / f'{self.in_tag}_specification.json'
        self.element_sim_props = self.out_el / 'sim_props.yaml'
        self.body_mes = self.out_el / f'{self.in_tag}_body_measurements.yaml'
        self.design_params = self.out_el / f'{self.in_tag}_design_params.yaml'
        
    def update_sim_paths(self) -> None:
        """
        Update simulation output paths.
        
        Sets paths for simulated garment files including OBJ, GLB, compressed PLY,
        and USD formats.
        """
        self.g_sim = self.out_el / f'{self.sim_tag}_sim.obj'
        self.g_sim_glb = self.out_el / f'{self.sim_tag}_sim.glb'
        self.g_sim_compressed = self.out_el / f'{self.sim_tag}_sim.ply'
        self.usd = self.out_el / f'{self.sim_tag}_simulation.usd'


    def render_path(self, camera_name: str = '') -> Path:
        """
        Get path for rendered image file.
        
        Parameters
        ----------
        camera_name : str, optional
            Name of the camera view (default: ''). If empty, uses default render name.
            
        Returns
        -------
        Path
            Path to the rendered image PNG file
        """
        fname = f'{self.sim_tag}_render_{camera_name}.png' if camera_name else f'{self.sim_tag}_render.png'
        return self.out_el / fname

