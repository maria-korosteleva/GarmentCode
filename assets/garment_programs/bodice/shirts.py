from copy import deepcopy

import pygarment as pyg
from assets.garment_programs.bodice import factory
from assets.garment_programs.bodice.bodice_halves.bodice_halves import BodiceHalf


class Shirt(pyg.Component):
    """Panel for the front of upper garments with darts to properly fit it to
    the shape"""

    def __init__(self, body: dict, design: dict, fitted: bool = False) -> None:
        name_with_params = f"{self.__class__.__name__}"
        super().__init__(name_with_params)

        design = self.eval_dep_params(design)

        self.right = BodiceHalf(f"right", body, design, fitted=fitted)
        self.left = BodiceHalf(
            f"left",
            body,
            design["left"] if design["left"]["enable_asym"]["v"] else design,
            fitted=fitted,
        ).mirror()

        self.stitching_rules.append(
            (self.right.interfaces["front_in"], self.left.interfaces["front_in"])
        )
        self.stitching_rules.append(
            (self.right.interfaces["back_in"], self.left.interfaces["back_in"])
        )

        # Adjust interface ordering for correct connectivity
        self.interfaces = {  # Bottom connection
            "bottom": pyg.Interface.from_multiple(
                self.right.interfaces["f_bottom"].reverse(),
                self.left.interfaces["f_bottom"],
                self.left.interfaces["b_bottom"].reverse(),
                self.right.interfaces["b_bottom"],
            )
        }

    def eval_dep_params(self, design: dict):
        # NOTE: Support for full collars with partially strapless top
        # or combination of paneled collar styles
        # requres further development
        # TODOLOW enable this one to work
        if design["left"]["enable_asym"]["v"]:
            # Force no collars since they are not compatible with each other
            design = deepcopy(design)
            design["collar"]["component"]["style"]["v"] = None
            design["left"]["collar"]["component"] = dict(style=dict(v=None))

            # Left-right design compatibility
            design["left"]["shirt"].update(length={})
            design["left"]["shirt"]["length"]["v"] = design["shirt"]["length"]["v"]

            design["left"]["collar"].update(fc_depth={}, bc_depth={})
            design["left"]["collar"]["fc_depth"]["v"] = design["collar"]["fc_depth"][
                "v"
            ]
            design["left"]["collar"]["bc_depth"]["v"] = design["collar"]["bc_depth"][
                "v"
            ]

        return design

    def length(self):
        return self.right.length()


class FittedShirt(Shirt):
    """Creates fitted shirt

    NOTE: Separate class is used for selection convenience.
    Even though most of the processing is the same
    (hence implemented with the same components except for panels),
    design parametrization differs significantly.
    With that, we decided to separate the top level names
    """

    def __init__(self, body, design) -> None:
        super().__init__(body, design, fitted=True)


@factory.register_builder("Shirt")
def build_shirt(body: dict, design: dict):
    return Shirt(body=body, design=design, fitted=False)


@factory.register_builder("FittedShirt")
def build_shirt(body: dict, design: dict):
    return Shirt(body=body, design=design, fitted=True)
