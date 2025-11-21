"""Garment material and fabric properties."""

from pydantic import BaseModel, Field


class GarmentMaterialProperties(BaseModel):
    """
    Material and fabric properties for garment simulation.
    
    This class encapsulates all physical material properties including bending stiffness,
    area preservation, spring constants, contact properties, and fabric characteristics.
    
    Attributes
    ----------
    garment_edge_ke : float
        Edge bending stiffness coefficient (elastic)
    garment_edge_kd : float
        Edge bending damping coefficient
    garment_tri_ke : float
        Triangle area preservation stiffness (elastic)
    garment_tri_kd : float
        Triangle area preservation damping
    garment_tri_ka : float
        Triangle area preservation stiffness (alternative)
    garment_tri_drag : float
        Triangle drag coefficient
    garment_tri_lift : float
        Triangle lift coefficient
    garment_density : float
        Fabric density
    garment_radius : float
        Fabric thickness/radius for collision detection
    spring_ke : float
        Spring constraint stiffness (elastic)
    spring_kd : float
        Spring constraint damping
    soft_contact_margin : float
        Soft contact margin for cloth-body collision
    soft_contact_ke : float
        Soft contact stiffness (elastic)
    soft_contact_kd : float
        Soft contact damping
    soft_contact_kf : float
        Soft contact friction stiffness
    soft_contact_mu : float
        Soft contact friction coefficient
    body_thickness : float
        Body collision thickness
    body_friction : float
        Body friction coefficient
    particle_ke : float
        Particle stiffness (not used in cloth sim, default value)
    particle_kd : float
        Particle damping (not used in cloth sim, default value)
    particle_kf : float
        Particle friction stiffness (not used in cloth sim, default value)
    particle_mu : float
        Particle friction coefficient (not used in cloth sim, default value)
    particle_cohesion : float
        Particle cohesion (not used in cloth sim, default value)
    particle_adhesion : float
        Particle adhesion (not used in cloth sim, default value)
    """
    
    # Bending properties
    garment_edge_ke: float = Field(default=50000.0, description="Edge bending stiffness coefficient (elastic)")
    garment_edge_kd: float = Field(default=10.0, description="Edge bending damping coefficient")
    
    # Area preservation
    garment_tri_ke: float = Field(default=10000.0, description="Triangle area preservation stiffness (elastic)")
    garment_tri_kd: float = Field(default=1.0, description="Triangle area preservation damping")
    garment_tri_ka: float = Field(default=10000.0, description="Triangle area preservation stiffness (alternative)")
    garment_tri_drag: float = Field(default=0.0, description="Triangle drag coefficient")
    garment_tri_lift: float = Field(default=0.0, description="Triangle lift coefficient")

    # Thickness and density
    garment_density: float = Field(default=1.0, description="Fabric density")
    garment_radius: float = Field(default=0.1, description="Fabric thickness/radius for collision detection")

    # Spring properties (Distance constraints)
    spring_ke: float = Field(default=50000.0, description="Spring constraint stiffness (elastic)")
    spring_kd: float = Field(default=10.0, description="Spring constraint damping")

    # Soft contact properties (contact between cloth and body)
    soft_contact_margin: float = Field(default=0.2, description="Soft contact margin for cloth-body collision")
    soft_contact_ke: float = Field(default=1000.0, description="Soft contact stiffness (elastic)")
    soft_contact_kd: float = Field(default=10.0, description="Soft contact damping")
    soft_contact_kf: float = Field(default=1000.0, description="Soft contact friction stiffness")
    soft_contact_mu: float = Field(default=0.5, description="Soft contact friction coefficient")

    # Body material
    # Note: These are set from options in SimConfig initialization
    body_thickness: float = Field(default=0.0, description="Body collision thickness")
    body_friction: float = Field(default=0.5, description="Body friction coefficient")

    # Particle properties (default values -- not used in cloth sim)
    particle_ke: float = Field(default=1.0e3, description="Particle stiffness (not used in cloth sim, default value)")
    particle_kd: float = Field(default=1.0e2, description="Particle damping (not used in cloth sim, default value)")
    particle_kf: float = Field(default=100.0, description="Particle friction stiffness (not used in cloth sim, default value)")
    particle_mu: float = Field(default=0.5, description="Particle friction coefficient (not used in cloth sim, default value)")
    particle_cohesion: float = Field(default=0.0, description="Particle cohesion (not used in cloth sim, default value)")
    particle_adhesion: float = Field(default=0.0, description="Particle adhesion (not used in cloth sim, default value)")

    model_config = {
        "frozen": False,  # Allow updates to body_thickness and body_friction
    }
