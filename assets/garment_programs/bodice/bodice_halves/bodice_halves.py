from copy import deepcopy

import numpy as np

from assets.garment_programs.sleeves import sleeves
import pygarment as pyg
from assets.garment_programs.bodice.bodice_halves.tee import (
    TorsoFrontHalfPanel,
    TorsoBackHalfPanel,
)
from assets.garment_programs.bodice.bodice_halves.bodice_panels import (
    BodiceBackHalf,
    BodiceFrontHalf,
)
# from assets.garment_programs.collars.collar_halves import base as collars
from assets.garment_programs.collars import factory as collar_factory


class BodiceHalf(pyg.Component):
    """Definition of a half of an upper garment with sleeves and collars"""

    def __init__(
        self, name: str, body: dict, design: dict, fitted: bool = True
    ) -> None:
        super().__init__(name)

        design = deepcopy(design)  # Recalculate freely!

        # Torso
        if fitted:
            self.ftorso = BodiceFrontHalf(f"{name}_ftorso", body, design).translate_by(
                [0, 0, 30]
            )
            self.btorso = BodiceBackHalf(f"{name}_btorso", body, design).translate_by(
                [0, 0, -25]
            )
        else:
            self.ftorso = TorsoFrontHalfPanel(
                f"{name}_ftorso", body, design
            ).translate_by([0, 0, 30])
            self.btorso = TorsoBackHalfPanel(
                f"{name}_btorso", body, design
            ).translate_by([0, 0, -25])

        # Interfaces
        self.interfaces.update(
            {
                "f_bottom": self.ftorso.interfaces["bottom"],
                "b_bottom": self.btorso.interfaces["bottom"],
                "front_in": self.ftorso.interfaces["inside"],
                "back_in": self.btorso.interfaces["inside"],
            }
        )

        # Sleeves/collar cuts
        self.sleeve = None
        self.collar_comp = None
        self.eval_dep_params(body, design)

        if (
            design["shirt"]["strapless"]["v"] and fitted
        ):  # NOTE: Strapless design only for fitted tops
            self.make_strapless(body, design)
        else:
            # Sleeves and collars
            self.add_sleeves(name, body, design)
            self.add_collars(name, body, design)
            self.stitching_rules.append(
                (self.ftorso.interfaces["shoulder"], self.btorso.interfaces["shoulder"])
            )  # tops

        # Main connectivity
        self.stitching_rules.append(
            (self.ftorso.interfaces["outside"], self.btorso.interfaces["outside"])
        )  # sides

    def eval_dep_params(self, body: dict, design: dict):

        # Sleeves
        # NOTE assuming the vertical side is the first argument
        max_cwidth = (
            self.ftorso.interfaces["shoulder_corner"].edges[0].length() - 1
        )  # cm
        min_cwidth = body["_armscye_depth"]
        v = design["sleeve"]["connecting_width"]["v"]
        design["sleeve"]["connecting_width"]["v"] = min(
            min_cwidth + min_cwidth * v, max_cwidth
        )

        # Collars
        # NOTE: Assuming the first is the top edge
        # Width
        # TODOLOW What if sleeve inclination is variable?
        # NOTE: Back panel is more narrow, so using it
        max_w = body["_base_sleeve_balance"] - 2  # 1 cm from default sleeve
        min_w = body["neck_w"]

        if design["collar"]["width"]["v"] >= 0:
            design["collar"]["width"]["v"] = width = pyg.utils.lin_interpolation(
                min_w, max_w, design["collar"]["width"]["v"]
            )
        else:
            design["collar"]["width"]["v"] = width = pyg.utils.lin_interpolation(
                0, min_w, 1 + design["collar"]["width"]["v"]
            )

        # Depth
        # Collar depth is given w.r.t. length.
        # adjust for the shoulder inclination
        tg = np.tan(np.deg2rad(body["_shoulder_incl"]))
        f_depth_adj = tg * (self.ftorso.get_width(0) - width / 2)
        b_depth_adj = tg * (self.btorso.get_width(0) - width / 2)

        max_f_len = (
            self.ftorso.interfaces["collar_corner"].edges[1].length()
            - tg * self.ftorso.get_width(0)
            - 1
        )  # cm
        max_b_len = (
            self.btorso.interfaces["collar_corner"].edges[1].length()
            - tg * self.btorso.get_width(0)
            - 1
        )  # cm

        design["collar"]["f_strapless_depth"] = {}
        design["collar"]["f_strapless_depth"]["v"] = min(
            design["collar"]["fc_depth"]["v"] * body["_bust_line"], max_f_len
        )
        design["collar"]["fc_depth"]["v"] = (
            design["collar"]["f_strapless_depth"]["v"] + f_depth_adj
        )

        design["collar"]["b_strapless_depth"] = {}
        design["collar"]["b_strapless_depth"]["v"] = min(
            design["collar"]["bc_depth"]["v"] * body["_bust_line"], max_b_len
        )
        design["collar"]["bc_depth"]["v"] = (
            design["collar"]["b_strapless_depth"]["v"] + b_depth_adj
        )

    def add_sleeves(self, name: str, body: dict, design: dict):
        self.sleeve = sleeves.Sleeve(
            name,
            body,
            design,
            front_w=self.ftorso.get_width,
            back_w=self.btorso.get_width,
        )

        _, f_sleeve_int = pyg.ops.cut_corner(
            self.sleeve.interfaces["in_front_shape"].edges,
            self.ftorso.interfaces["shoulder_corner"],
            verbose=self.verbose,
        )
        _, b_sleeve_int = pyg.ops.cut_corner(
            self.sleeve.interfaces["in_back_shape"].edges,
            self.btorso.interfaces["shoulder_corner"],
            verbose=self.verbose,
        )

        if not design["sleeve"]["sleeveless"]["v"]:
            # Ordering
            bodice_sleeve_int = pyg.Interface.from_multiple(
                f_sleeve_int.reverse(with_edge_dir_reverse=True),
                b_sleeve_int.reverse(),
            )
            self.stitching_rules.append(
                (self.sleeve.interfaces["in"], bodice_sleeve_int)
            )

            # NOTE: This is a heuristic tuned for arm poses 30 deg-60 deg
            # used in the dataset
            # FIXME Needs a better general solution
            gap = -1 - body["arm_pose_angle"] / 10
            self.sleeve.place_by_interface(
                self.sleeve.interfaces["in"],
                bodice_sleeve_int,
                gap=gap,
                alignment="top",
            )

        # Add edge labels
        f_sleeve_int.edges.propagate_label(f"{self.name}_armhole")
        b_sleeve_int.edges.propagate_label(f"{self.name}_armhole")

    def add_collars(self, name: str, body: dict, design: dict):
        # Front
        # collar_type = getattr(
        #     collars,
        #     str(design["collar"]["component"]["style"]["v"]),
        #     default=collars.NoPanelsCollar,
        # )
        # self.collar_comp = collar_type(name, body, design)
        if design["collar"]["component"]["style"]["v"] in collar_factory._REGISTERED_COLLAR_CLS:
            collar_type = design["collar"]["component"]["style"]["v"]
        else:
            collar_type = "NoPanelsCollar"

        self.collar_comp = collar_factory.build(
            name=collar_type, string_name=name, body=body, design=design
        )

        # Project shape
        _, fc_interface = pyg.ops.cut_corner(
            self.collar_comp.interfaces["front_proj"].edges,
            self.ftorso.interfaces["collar_corner"],
            verbose=self.verbose,
        )
        _, bc_interface = pyg.ops.cut_corner(
            self.collar_comp.interfaces["back_proj"].edges,
            self.btorso.interfaces["collar_corner"],
            verbose=self.verbose,
        )

        # Add stitches/interfaces
        if "bottom" in self.collar_comp.interfaces:
            self.stitching_rules.append(
                (
                    pyg.Interface.from_multiple(fc_interface, bc_interface),
                    self.collar_comp.interfaces["bottom"],
                )
            )

        # Upd front interfaces accordingly
        if "front" in self.collar_comp.interfaces:
            self.interfaces["front_collar"] = self.collar_comp.interfaces["front"]
            self.interfaces["front_in"] = pyg.Interface.from_multiple(
                self.ftorso.interfaces["inside"], self.interfaces["front_collar"]
            )
        if "back" in self.collar_comp.interfaces:
            self.interfaces["back_collar"] = self.collar_comp.interfaces["back"]
            self.interfaces["back_in"] = pyg.Interface.from_multiple(
                self.btorso.interfaces["inside"], self.interfaces["back_collar"]
            )

        # Add edge labels
        fc_interface.edges.propagate_label(f"{self.name}_collar")
        bc_interface.edges.propagate_label(f"{self.name}_collar")

    def make_strapless(self, body: dict, design: dict):

        out_depth = design["sleeve"]["connecting_width"]["v"]
        f_in_depth = design["collar"]["f_strapless_depth"]["v"]
        b_in_depth = design["collar"]["b_strapless_depth"]["v"]

        # Shoulder adjustment for the back
        # TODOLOW Shoulder adj evaluation should be a function
        shoulder_angle = np.deg2rad(body["_shoulder_incl"])
        sleeve_balance = body["_base_sleeve_balance"] / 2
        back_w = self.btorso.get_width(0)
        shoulder_adj = np.tan(shoulder_angle) * (back_w - sleeve_balance)
        out_depth -= shoulder_adj

        # Upd back
        self._adjust_top_level(self.btorso, out_depth, b_in_depth)

        # Front depth determined by ~compensating for lenght difference
        len_back = self.btorso.interfaces["outside"].edges.length()
        len_front = self.ftorso.interfaces["outside"].edges.length()
        self._adjust_top_level(
            self.ftorso, out_depth, f_in_depth, target_remove=(len_front - len_back)
        )

        # Placement
        # NOTE: The commented line places the top a bit higher, increasing the chanced of correct drape
        # Surcumvented by attachment constraint, so removed for nicer alignment in asymmetric garments
        # self.translate_by([0, out_depth - body['_armscye_depth'] * 0.75, 0])   # adjust for better localisation

        # Add a label
        self.ftorso.interfaces["shoulder"].edges.propagate_label("strapless_top")
        self.btorso.interfaces["shoulder"].edges.propagate_label("strapless_top")

    def _adjust_top_level(self, panel, out_level: float, in_level: float, target_remove: bool = None):
        """Crops the top of the bodice front/back panel for strapless style

        * out_length_diff -- if set, determined the length difference that should be compensates
        after cutting the depth
        """
        # TODOLOW Should this be the panel's function?

        panel_top = panel.interfaces["shoulder"].edges[0]
        min_y = min(panel_top.start[1], panel_top.end[1])

        # Order vertices
        ins, out = panel_top.start, panel_top.end
        if panel_top.start[1] < panel_top.end[1]:
            ins, out = out, ins

        # Inside is a simple vertical line and can be adjusted by chaning Y value
        ins[1] = min_y - in_level

        # Outside could be inclined, so needs further calculations
        outside_edge = panel.interfaces["outside"].edges[-1]
        bot, top = outside_edge.start, outside_edge.end
        if bot is out:
            bot, top = top, bot

        if target_remove is not None:
            # Adjust the depth to remove this length exactly
            angle_sin = abs(out[1] - bot[1]) / outside_edge.length()
            curr_remove = out_level / angle_sin
            length_diff = target_remove - curr_remove
            adjustment = length_diff * angle_sin
            out_level += adjustment

        angle_cotan = abs(out[0] - bot[0]) / abs(out[1] - bot[1])
        out[0] -= out_level * angle_cotan
        out[1] = min_y - out_level

    def length(self):
        return self.btorso.length()
