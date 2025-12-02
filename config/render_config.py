"""Render configuration classes."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UVTextureConfig(BaseModel):
    """UV texture configuration for garment rendering.
    
    Attributes
    ----------
    seam_width : float
        Width of seams in texture (in cm)
    dpi : int
        Dots per inch for texture resolution
    fabric_grain_texture_path : Optional[str]
        Path to fabric grain texture image (optional)
    fabric_grain_resolution : int
        Resolution of fabric grain texture
    """
    seam_width: float = Field(default=0.5, description="Width of seams in texture (in cm)")
    dpi: int = Field(default=1500, description="Dots per inch for texture resolution")
    fabric_grain_texture_path: Optional[str] = Field(
        default=None,
        description="Path to fabric grain texture image (optional)"
    )
    fabric_grain_resolution: int = Field(default=5, description="Resolution of fabric grain texture")


class RenderConfig(BaseModel):
    """Render configuration for garment visualization.
    
    Attributes
    ----------
    resolution : list[int]
        Render resolution as [width, height] in pixels
    sides : list[str]
        List of sides to render (e.g., ['front', 'back', 'straight-front', 'straight-back'])
    front_camera_location : Optional[list[float]]
        Optional camera location for front view as [x, y, z]
    straight_front_camera_location : Optional[list[float]]
        Optional camera location for straight-front view as [x, y, z]
    straight_back_camera_location : Optional[list[float]]
        Optional camera location for straight-back view as [x, y, z]
    uv_texture : UVTextureConfig
        UV texture configuration
    """
    resolution: list[int] = Field(
        default_factory=lambda: [800, 800],
        description="Render resolution as [width, height] in pixels"
    )
    sides: list[str] = Field(
        default_factory=lambda: ['front', 'back'],
        description="List of sides to render (e.g., ['front', 'back', 'straight-front', 'straight-back'])"
    )
    front_camera_location: Optional[list[float]] = Field(
        default=None,
        description="Optional camera location for front view as [x, y, z]"
    )
    straight_front_camera_location: Optional[list[float]] = Field(
        default=None,
        description="Optional camera location for straight-front view as [x, y, z]"
    )
    straight_back_camera_location: Optional[list[float]] = Field(
        default=None,
        description="Optional camera location for straight-back view as [x, y, z]"
    )
    uv_texture: UVTextureConfig = Field(
        default_factory=UVTextureConfig,
        description="UV texture configuration"
    )
    
    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v):
        if len(v) != 2:
            raise ValueError('resolution must be a list of exactly 2 integers [width, height]')
        if not all(isinstance(x, int) for x in v):
            raise ValueError('resolution must contain only integers')
        return v
    
    @field_validator('front_camera_location', 'straight_front_camera_location', 'straight_back_camera_location')
    @classmethod
    def validate_camera_location(cls, v):
        if v is not None and len(v) != 3:
            raise ValueError('camera_location must be a list of exactly 3 floats [x, y, z]')
        return v

