import pygarment as pyg
from assets.garment_programs.collars import factory
from assets.garment_programs.collars.collar_halves import \
    factory as collar_curve_factory


@factory.register_builder("NoPanelsCollar")
class NoPanelsCollar(pyg.Component):
    """Face collar class that only forms the projected shapes"""

    def __init__(self, string_name: str, body: dict, design: dict) -> None:
        super().__init__(string_name)

        # Front
        f_collar = collar_curve_factory.build(
            name=design["collar"]["f_collar"]["v"],
            depth=design["collar"]["fc_depth"]["v"],
            width=design["collar"]["width"]["v"],
            angle=design["collar"]["fc_angle"]["v"],
            flip=design["collar"]["f_flip_curve"]["v"],
            x=design["collar"]["f_bezier_x"]["v"],
            y=design["collar"]["f_bezier_y"]["v"],
            verbose=self.verbose,
        )

        # Back
        b_collar = collar_curve_factory.build(
            name=design["collar"]["b_collar"]["v"],
            depth=design["collar"]["bc_depth"]["v"],
            width=design["collar"]["width"]["v"],
            angle=design["collar"]["bc_angle"]["v"],
            flip=design["collar"]["b_flip_curve"]["v"],
            x=design["collar"]["b_bezier_x"]["v"],
            y=design["collar"]["b_bezier_y"]["v"],
            verbose=self.verbose,
        )

        self.interfaces = {
            "front_proj": pyg.Interface(self, f_collar),
            "back_proj": pyg.Interface(self, b_collar),
        }

    def length(self):
        return 0
