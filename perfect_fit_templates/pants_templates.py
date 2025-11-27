from collections import namedtuple
from enum import Enum

from pattern_definitions.pants_design import PantsDesign
from pattern_definitions.body_definition import BodyDefinition


# Vertical ratios for leg length:
THIGH_TO_KNEE_LEG_RATIO = 0.5
KNEE_TO_CALF_LEG_RATIO = 0.25
CALF_TO_ANKLE_LEG_RATIO = 0.25


class GeneralFit(Enum):
    """Enum for thigh & hips width ratio in relation to horizontal leg line at the crotch"""
    WIDE = 1.1
    REGULAR = 1.02
    TIGHT = 0.9
    SUPER_TIGHT = 0.75


class RaiseWaist(Enum):
    """Enum for waist fit. Factors are relative to the body's waist level."""
    HIGH = 1.0
    MID = 0.9
    LOW = 0.85


class CrotchDisplacementRatio(Enum):
    """Enum for crotch displacement ratio in relation to leg length"""
    INSIDE_CROTCH = -0.1
    AT_CROTCH = 0
    LOW_CROTCH = 0.08
    HANGY = 0.16


class LegLength(Enum):
    """Enum for leg length ratio in relation to the body's leg length"""
    SHORT_SHORTS = 0.2
    SHORTS = 0.3
    CAPRI = 0.8
    ANKLE = 0.9
    FULL = 0.95
    LONG = 1


SleeveConfig = namedtuple('SleeveConfig', ['knee_ratio', 'calf_ratio', 'ankle_ratio', 'knee_bias', 'calf_bias', 'ankle_bias'])


class PerfectFitPantsStyleSpec(Enum):
    """Enum for pants style specifications with SleeveConfig namedtuple values."""
    TIGHTS = SleeveConfig(
        knee_ratio=2/3,
        calf_ratio=0.5,
        ankle_ratio=0.4,
        knee_bias=0,
        calf_bias=0,
        ankle_bias=0,
    )
    SKINNY = SleeveConfig(
        knee_ratio=2/3,
        calf_ratio=0.53,
        ankle_ratio=0.4,
        knee_bias=-3.8,
        calf_bias=1.8,
        ankle_bias=7.4,
    )
    STRAIGHT = SleeveConfig(
        knee_ratio=0.5,
        calf_ratio=0.5,
        ankle_ratio=0.5,
        knee_bias=12.5,
        calf_bias=10.2,
        ankle_bias=7.8,
    )
    BOOT_CUT = SleeveConfig(
        knee_ratio=0.5,
        calf_ratio=0.5,
        ankle_ratio=0.5,
        knee_bias=8.5,
        calf_bias=13,
        ankle_bias=19.5,
    )
    FLARE = SleeveConfig(
        knee_ratio=0.5,
        calf_ratio=0.5,
        ankle_ratio=0.5,
        knee_bias=12.5,
        calf_bias=17.5,
        ankle_bias=25.2,
    )
    WIDE_LEG = SleeveConfig(
        knee_ratio=0.5,
        calf_ratio=0.5,
        ankle_ratio=0.5,
        knee_bias=19,
        calf_bias=22.1,
        ankle_bias=25.2,
    )


class PerfectFitPantsDesign:
    """
    Perfect fit pants design.
    """

    RATIO_RAISE_BACK_TO_FRONT: float = 1.1

    _waist: float
    _hips: float
    _front_rise: float
    _back_rise: float
    _width_hips: float
    _width_thigh: float
    _width_gusset_crotch: float
    _crotch_shift_ratio: float
    _length_waist_to_hip: float
    _length_thigh_to_knee: float
    _length_knee_to_calf: float
    _length_calf_to_ankle: float
    _width_knee: float
    _width_calf: float
    _width_ankle: float

    def __init__(self,
                 body_definition: BodyDefinition,
                 raise_to_waist_ratio: RaiseWaist,
                 crotch_displacement_ratio: CrotchDisplacementRatio,
                 general_fit_ratio: GeneralFit,
                 leg_length_ratio: LegLength,
                 pants_style_spec: PerfectFitPantsStyleSpec,
                ) -> None:
        """Initialize pants template.
        
        Parameters:
        -----------
        body_definition: BodyDefinition
            The body definition.
        raise_to_waist_ratio: RaiseWaist
            The raise to waist ratio.
        crotch_displacement_ratio: CrotchDisplacementRatio
            The crotch displacement ratio.
        general_fit_ratio: GeneralFit
            The general fit ratio.
        leg_length_ratio: LegLength
            The leg length ratio.
        pants_style_spec: PerfectFitPantsStyleSpec
            The pants style specification. Each enum member's value is a SleeveConfig
            namedtuple containing knee_ratio, calf_ratio, ankle_ratio, knee_bias,
            calf_bias, and ankle_bias.
        """

        style_config: SleeveConfig = pants_style_spec.value

        waist_half = body_definition.waist / 2
        hips_half = body_definition.hips / 2
        waist_to_crotch = body_definition.crotch_hip_diff + body_definition.hips_line

        self._front_rise: float = (
            waist_to_crotch * raise_to_waist_ratio.value +
            max(0, body_definition.computed_leg_length * crotch_displacement_ratio.value)
        )
        self._back_rise: float = (
            waist_to_crotch * raise_to_waist_ratio.value * self.RATIO_RAISE_BACK_TO_FRONT +
            max(0, body_definition.computed_leg_length * crotch_displacement_ratio.value)
        )
        self._waist: float = waist_half * (general_fit_ratio.value if general_fit_ratio == GeneralFit.SUPER_TIGHT else 1)
        self._width_hips: float = hips_half * general_fit_ratio.value
        self._width_thigh: float = body_definition.leg_circ / 2 * general_fit_ratio.value

        min_ext = body_definition.leg_circ - body_definition.hips / 2  + 5  # 2 inch ease: from pattern making book 
        front_hip = (body_definition.hips - body_definition.hip_back_width) / 2
        crotch_extention = min_ext
        front_extention = front_hip / 4    # From pattern making book
        back_extention = crotch_extention - front_extention
        self._width_gusset_crotch: float = (front_extention + back_extention) / 2 * general_fit_ratio.value

        self._length_waist_to_hip: float = body_definition.hips_line * raise_to_waist_ratio.value
        self._crotch_shift_ratio: float = crotch_displacement_ratio.value
        body_definition.fit_waist_level = body_definition.computed_waist_level + waist_to_crotch * (raise_to_waist_ratio.value * self.RATIO_RAISE_BACK_TO_FRONT - 1)

        # Leg parameters:
        crotch_to_ankle_ratio = leg_length_ratio.value - body_definition.crotch_hip_diff / body_definition.computed_leg_length
        self._length_thigh_to_knee: float = body_definition.computed_leg_length * (THIGH_TO_KNEE_LEG_RATIO  - self._crotch_shift_ratio) * crotch_to_ankle_ratio
        self._length_knee_to_calf: float = body_definition.computed_leg_length * KNEE_TO_CALF_LEG_RATIO * crotch_to_ankle_ratio
        self._length_calf_to_ankle: float = body_definition.computed_leg_length * CALF_TO_ANKLE_LEG_RATIO * crotch_to_ankle_ratio
        
        self._width_knee: float = general_fit_ratio.value * (body_definition.leg_circ / 2 * style_config.knee_ratio + style_config.knee_bias)
        self._width_calf: float = general_fit_ratio.value * (body_definition.leg_circ / 2 * style_config.calf_ratio + style_config.calf_bias)
        self._width_ankle: float = general_fit_ratio.value * (body_definition.leg_circ / 2 * style_config.ankle_ratio + style_config.ankle_bias)

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
