from abc import ABC, abstractmethod
from enum import Enum

from pattern_definitions.pants_design import PantsDesign
from pattern_definitions.body_definition import BodyDefinition



class WaistFit(Enum):
    """Enum for waist fit."""
    HIGH = 1.1
    MID = 1
    LOW = 0.9


class CrotchDisplacementRatio(Enum):
    """Enum for crotch displacement ratio in relation to leg length"""
    AT_CROTCH = 0
    LOW_CROTCH = 0.08
    HANGY = 0.16


class HipPosition(Enum):
    """Enum for hip position ratio in relation to hipsline"""
    REGULAR = 1.05
    TIGHT = 0.9


class ThighPosition(Enum):
    """Enum for thigh position ratio in relation to horizontal line at the crotch"""
    WIDE = 1.1
    REGULAR = 1.05
    TIGHT = 0.9


class PantsTemplateBase(ABC):
    """
    Abstract base class for pants templates to be used in perfect fit simulation.
    """

    RATIO_RAISE_BACK_TO_FRONT: float = 1.05

    _body_definition: BodyDefinition
    _waist: float
    _hips: float
    _front_rise: float
    _back_rise: float
    _width_hips: float
    _width_thigh: float
    _width_gusset_crotch: float
    _crotch_shift_ratio: float
    _length_waist_to_hip: float

    def __init__(self,
                 body_definition: BodyDefinition,
                 raise_to_waist_ratio: WaistFit,
                 crotch_displacement_ratio: CrotchDisplacementRatio,
                 hip_position_ratio: HipPosition,
                 thigh_position_ratio: ThighPosition,
                ) -> None:
        """Initialize pants template.
        
        Parameters:
        -----------
        body_definition: BodyDefinition
            The body definition.
        """
        self._body_definition = body_definition

        waist_half = self._body_definition.waist / 2
        hips_half = self._body_definition.hips / 2
        waist_to_crotch = self._body_definition.crotch_hip_diff + self._body_definition.hips_line

        self._front_rise: float = (
            waist_to_crotch * raise_to_waist_ratio.value +
            self._body_definition.computed_leg_length * crotch_displacement_ratio.value
        )
        self._back_rise: float = (
            waist_to_crotch * raise_to_waist_ratio.value * self.RATIO_RAISE_BACK_TO_FRONT +
            self._body_definition.computed_leg_length * crotch_displacement_ratio.value
        )
        self._waist: float = waist_half
        self._width_hips: float = hips_half * hip_position_ratio.value
        self._width_thigh: float = self._body_definition.leg_circ * thigh_position_ratio.value / 2

        min_ext = body_definition.leg_circ - body_definition.hips / 2  + 5  # 2 inch ease: from pattern making book 
        front_hip = (body_definition.hips - body_definition.hip_back_width) / 2
        crotch_extention = min_ext * thigh_position_ratio.value  
        front_extention = front_hip / 4    # From pattern making book
        back_extention = crotch_extention - front_extention
        self._width_gusset_crotch: float = (front_extention + back_extention) / 2

        self._length_waist_to_hip: float = body_definition.hips_line
        self._crotch_shift_ratio: float = crotch_displacement_ratio.value

    @abstractmethod
    def get_design(self) -> PantsDesign:
        """Abstract method to retrieve pants design."""
        raise NotImplementedError("Subclasses must implement this method")


class LoosePantsSraightLeg(PantsTemplateBase):
    """Loose pants with straight legs."""

    _length_thigh_to_knee: float
    _length_knee_to_calf: float
    _length_calf_to_ankle: float
    _width_knee: float
    _width_calf: float
    _width_ankle: float

    def __init__(self,
                 body_definition: BodyDefinition,
                 raise_to_waist_ratio: WaistFit = WaistFit.MID,
                 crotch_displacement_ratio: CrotchDisplacementRatio = CrotchDisplacementRatio.AT_CROTCH,
                 hip_position_ratio: HipPosition = HipPosition.REGULAR,
                 thigh_position_ratio: ThighPosition = ThighPosition.REGULAR,
                ) -> None:

        super().__init__(body_definition, raise_to_waist_ratio, crotch_displacement_ratio, hip_position_ratio, thigh_position_ratio)

        self._length_thigh_to_knee: float = self._body_definition.computed_leg_length * 0.4
        self._length_knee_to_calf: float = self._body_definition.computed_leg_length * 0.2
        self._length_calf_to_ankle: float = self._body_definition.computed_leg_length * 0.2
        self._width_knee: float = self._body_definition.leg_circ * 0.4
        self._width_calf: float = self._body_definition.leg_circ * 0.4
        self._width_ankle: float = self._body_definition.leg_circ * 0.5



    def get_design(self) -> PantsDesign:
        """Get pants design."""
        pants_dict = {
            'front_rise': {'v': self._front_rise},
            'back_rise': {'v': self._back_rise},
            'length_waist_to_hip': {'v': self._length_waist_to_hip},
            'length_1': {'v': self._length_thigh_to_knee},
            'length_2': {'v': self._length_knee_to_calf},
            'length_3': {'v': self._length_calf_to_ankle},
            'waist': {'v': self._waist},
            'width_1': {'v': self._width_thigh},
            'width_2': {'v': self._width_knee},
            'width_3': {'v': self._width_calf},
            'width_4': {'v': self._width_ankle},
            'width_hips': {'v': self._width_hips},
            'width_gusset_crotch': {'v': self._width_gusset_crotch},
            'crotch_shift_ratio': {'v': self._crotch_shift_ratio},
            'cuff': {}  # Empty dict will use default CuffDesign values
        }
        return PantsDesign(pants_dict)