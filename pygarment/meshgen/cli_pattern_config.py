"""Configuration class for CLI pattern generation.

This module provides a simple, type-safe configuration class for pattern generation
via command-line interface, replacing the more complex Properties class for this
specific use case.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger


@dataclass
class CLIPatternConfig:
    """Configuration for CLI pattern generation.
    
    This class holds all the necessary configuration properties for generating
    sewing patterns from design files via the command-line interface. It replaces
    dictionary-based configuration with a type-safe class structure.
    
    Attributes
    ----------
    design_file : Path
        Path to the design parameters YAML file.
    body_name : str
        Name of the body model to use (without .yaml extension).
    output_name : str
        Base name for the pattern output folder.
    perfect_fit : bool
        Whether to use perfect fit garment specification format.
    to_subfolders : bool
        Whether to save patterns to subfolders (legacy option, currently unused).
    output_folder : Optional[str]
        Generated output folder name (includes timestamp). Set automatically
        during pattern generation. Default is None.
    """
    
    design_file: Path
    body_name: str
    output_name: str
    perfect_fit: bool = False
    to_subfolders: bool = True
    output_folder: Optional[str] = field(default=None, init=False)
    
    def __post_init__(self) -> None:
        """Validate and normalize configuration after initialization."""
        # Ensure design_file is a Path object
        if isinstance(self.design_file, str):
            self.design_file = Path(self.design_file)
        
        # Validate design file exists
        if not self.design_file.exists():
            raise FileNotFoundError(
                f"Design file not found: {self.design_file}"
            )
        
        # Remove .yaml extension from body_name if present
        if self.body_name.endswith('.yaml'):
            self.body_name = self.body_name[:-5]
    
    def generate_output_folder_name(self, regenerate: bool = False) -> str:
        """Generate a unique output folder name with timestamp.
        
        Parameters
        ----------
        regenerate : bool, optional
            If True and output_folder is already set, creates a new name with
            '_regen' suffix. Default is False.
        
        Returns
        -------
        str
            Generated output folder name.
        """
        if regenerate and self.output_folder is not None:
            base_name = f"{self.output_folder}_regen"
        else:
            base_name = self.output_name
        
        timestamp = datetime.now().strftime('%y%m%d-%H-%M-%S')
        self.output_folder = f"{base_name}_{timestamp}"
        
        logger.debug(f"Generated output folder name: {self.output_folder}")
        return self.output_folder
    
    @property
    def pattern_output_name(self) -> str:
        """Get the pattern output name (output_folder if set, otherwise output_name).
        
        Returns
        -------
        str
            Pattern output name.
        """
        return self.output_folder if self.output_folder is not None else self.output_name
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        return (
            f"CLIPatternConfig("
            f"design_file={self.design_file}, "
            f"body_name={self.body_name}, "
            f"output_name={self.output_name}, "
            f"perfect_fit={self.perfect_fit}, "
            f"output_folder={self.output_folder})"
        )

