from scipy.spatial.transform import Rotation as R

import pygarment as pyg
from assets.garment_programs.bands import factory as band_factory
from assets.garment_programs.collars import factory
from assets.garment_programs.collars.collar_halves import \
    factory as collar_curve_factory

# # ------ Collars with panels ------


@factory.register_builder("Turtle")
class Turtle(pyg.Component):

    def __init__(self, tag: str, body: dict, design: dict) -> None:
        super().__init__(f"Turtle_{tag}")

        depth = design["collar"]["component"]["depth"]["v"]

        # --Projecting shapes--
        # f_collar = CircleNeckHalf(
        #     design["collar"]["fc_depth"]["v"], design["collar"]["width"]["v"]
        # )
        # b_collar = CircleNeckHalf(
        #     design["collar"]["bc_depth"]["v"], design["collar"]["width"]["v"]
        # )
        f_collar = collar_curve_factory.build(
            name="CircleNeckHalf",
            depth=design["collar"]["fc_depth"]["v"],
            width=design["collar"]["width"]["v"],
        )
        b_collar = collar_curve_factory.build(
            name="CircleNeckHalf",
            depth=design["collar"]["bc_depth"]["v"],
            width=design["collar"]["width"]["v"],
        )

        self.interfaces = {
            "front_proj": pyg.Interface(self, f_collar),
            "back_proj": pyg.Interface(self, b_collar),
        }

        # -- Panels --
        length_f, length_b = f_collar.length(), b_collar.length()
        height_p = body["height"] - body["head_l"] + depth

        # self.front = StraightBandPanel(
        #     f"{tag}_collar_front", length_f, depth
        # ).translate_by([-length_f / 2, height_p, 10])
        # self.back = StraightBandPanel(
        #     f"{tag}_collar_back", length_b, depth
        # ).translate_by([-length_b / 2, height_p, -10])
        self.front = band_factory.build(
            name="StraightBandPanel",
            string_name=f"{tag}_collar_front",
            width=length_f,
            depth=depth,
        ).translate_by([-length_f / 2, height_p, 10])
        self.back = band_factory.build(
            name="StraightBandPanel",
            string_name=f"{tag}_collar_back",
            width=length_b,
            depth=depth,
        ).translate_by([-length_b / 2, height_p, -10])

        self.stitching_rules.append(
            (self.front.interfaces["right"], self.back.interfaces["right"])
        )

        self.interfaces.update(
            {
                "front": self.front.interfaces["left"],
                "back": self.back.interfaces["left"],
                "bottom": pyg.Interface.from_multiple(
                    self.front.interfaces["bottom"], self.back.interfaces["bottom"]
                ),
            }
        )

    def length(self):
        return self.interfaces["back"].edges.length()


class SimpleLapelPanel(pyg.Panel):
    """A panel for the front part of simple Lapel"""

    def __init__(self, name, length, max_depth) -> None:
        super().__init__(name)

        self.edges = pyg.EdgeSeqFactory.from_verts(
            [0, 0], [max_depth, 0], [max_depth, -length]
        )

        self.edges.append(
            pyg.CurveEdge(self.edges[-1].end, self.edges[0].start, [[0.7, 0.2]])
        )

        self.interfaces = {
            "to_collar": pyg.Interface(self, self.edges[0]),
            "to_bodice": pyg.Interface(self, self.edges[1]),
        }


@factory.register_builder("SimpleLapel")
class SimpleLapel(pyg.Component):

    def __init__(self, tag, body, design) -> None:
        super().__init__(f"Turtle_{tag}")

        depth = design["collar"]["component"]["depth"]["v"]
        standing = design["collar"]["component"]["lapel_standing"]["v"]

        # --Projecting shapes--
        # Any front one!
        # collar_type = globals()[design["collar"]["f_collar"]["v"]]
        # f_collar = collar_type(
        #     design["collar"]["fc_depth"]["v"],
        #     design["collar"]["width"]["v"],
        #     angle=design["collar"]["fc_angle"]["v"],
        #     flip=design["collar"]["f_flip_curve"]["v"],
        # )
        # b_collar = CircleNeckHalf(
        #     design["collar"]["bc_depth"]["v"], design["collar"]["width"]["v"]
        # )
        f_collar = collar_curve_factory.build(
            name=design["collar"]["f_collar"]["v"],
            depth=design["collar"]["fc_depth"]["v"],
            width=design["collar"]["width"]["v"],
            angle=design["collar"]["fc_angle"]["v"],
            flip=design["collar"]["f_flip_curve"]["v"],
        )
        b_collar = collar_curve_factory.build(
            name="CircleNeckHalf",
            depth=design["collar"]["bc_depth"]["v"],
            width=design["collar"]["width"]["v"],
        )

        self.interfaces = {
            "front_proj": pyg.Interface(self, f_collar),
            "back_proj": pyg.Interface(self, b_collar),
        }

        # -- Panels --
        length_f, length_b = f_collar.length(), b_collar.length()
        height_p = body["height"] - body["head_l"] + depth * 2

        self.front = SimpleLapelPanel(
            f"{tag}_collar_front", length_f, depth
        ).translate_by([-depth * 2, height_p, 35])
        # TODOLOW This should be related with the bodice panels' placement

        if standing:
            # self.back = StraightBandPanel(
            #     f"{tag}_collar_back", length_b, depth
            # ).translate_by([-length_b / 2, height_p, -10])
            self.back = band_factory.build(
                name="StraightBandPanel",
                string_name=f"{tag}_collar_back",
                width=length_b,
                depth=depth,
            ).translate_by([-length_b / 2, height_p, -10])
        else:
            # A curved back panel that follows the collar opening
            rad, angle, _ = b_collar[0].as_radius_angle()
            # self.back = CircleArcPanel(
            #     f"{tag}_collar_back", rad, depth, angle
            # ).translate_by([-length_b, height_p, -10])
            self.back = band_factory.build(
                name="CircleArcPanel",
                string_name=f"{tag}_collar_back",
                top_rad=rad,
                length=depth,
                angle=angle,
            ).translate_by([-length_b, height_p, -10])
            self.back.rotate_by(R.from_euler("XYZ", [90, 45, 0], degrees=True))

        if standing:
            self.back.interfaces["right"].set_right_wrong(True)

        self.stitching_rules.append(
            (self.front.interfaces["to_collar"], self.back.interfaces["right"])
        )

        self.interfaces.update(
            {
                #'front': NOTE: no front interface here
                "back": self.back.interfaces["left"],
                "bottom": pyg.Interface.from_multiple(
                    self.front.interfaces["to_bodice"].set_right_wrong(True),
                    (
                        self.back.interfaces["bottom"]
                        if standing
                        else self.back.interfaces["top"].set_right_wrong(True)
                    ),
                ),
            }
        )

    def length(self):
        return self.interfaces["back"].edges.length()


class HoodPanel(pyg.Panel):
    """A panel for the side of the hood"""

    def __init__(
        self, name, f_depth, b_depth, f_length, b_length, width, in_length, depth
    ) -> None:
        super().__init__(name)

        width = width / 2  # Panel covers one half only
        length = in_length + width / 2

        # Bottom-back
        bottom_back_in = pyg.CurveEdge(
            [-width, -b_depth], [0, 0], [[0.3, -0.2], [0.6, 0.2]]
        )
        bottom_back = pyg.ops.curve_match_tangents(
            bottom_back_in.as_curve(),
            [1, 0],  # Full opening is vertically aligned
            [1, 0],
            target_len=b_length,
            return_as_edge=True,
            verbose=self.verbose,
        )
        self.edges.append(bottom_back)

        # Bottom front
        bottom_front_in = pyg.CurveEdge(
            self.edges[-1].end, [width, -f_depth], [[0.3, 0.2], [0.6, -0.2]]
        )
        bottom_front = pyg.ops.curve_match_tangents(
            bottom_front_in.as_curve(),
            [1, 0],  # Full opening is vertically aligned
            [1, 0],
            target_len=f_length,
            return_as_edge=True,
            verbose=self.verbose,
        )
        self.edges.append(bottom_front)

        # Front-top straight section
        self.edges.append(
            pyg.EdgeSeqFactory.from_verts(
                self.edges[-1].end, [width * 1.2, length], [width * 1.2 - depth, length]
            )
        )
        # Back of the hood
        self.edges.append(
            pyg.CurveEdge(self.edges[-1].end, self.edges[0].start, [[0.2, -0.5]])
        )

        self.interfaces = {
            "to_other_side": pyg.Interface(self, self.edges[-2:]),
            "to_bodice": pyg.Interface(self, self.edges[0:2]).reverse(),
        }

        self.rotate_by(R.from_euler("XYZ", [0, -90, 0], degrees=True))
        self.translate_by([-width, 0, 0])


@factory.register_builder("Hood2Panels")
class Hood2Panels(pyg.Component):

    def __init__(self, tag, body, design) -> None:
        super().__init__(f"Hood_{tag}")

        # --Projecting shapes--
        width = design["collar"]["width"]["v"]
        # f_collar = CircleNeckHalf(
        #     design["collar"]["fc_depth"]["v"], design["collar"]["width"]["v"]
        # )
        # b_collar = CircleNeckHalf(
        #     design["collar"]["bc_depth"]["v"], design["collar"]["width"]["v"]
        # )
        f_collar = collar_curve_factory.build(
            name="CircleNeckHalf",
            depth=design["collar"]["fc_depth"]["v"],
            width=design["collar"]["width"]["v"],
        )
        b_collar = collar_curve_factory.build(
            name="CircleNeckHalf",
            depth=design["collar"]["bc_depth"]["v"],
            width=design["collar"]["width"]["v"],
        )

        self.interfaces = {
            "front_proj": pyg.Interface(self, f_collar),
            "back_proj": pyg.Interface(self, b_collar),
        }

        # -- Panel --
        self.panel = HoodPanel(
            f"{tag}_hood",
            design["collar"]["fc_depth"]["v"],
            design["collar"]["bc_depth"]["v"],
            f_length=f_collar.length(),
            b_length=b_collar.length(),
            width=width,
            in_length=body["head_l"]
            * design["collar"]["component"]["hood_length"]["v"],
            depth=width / 2 * design["collar"]["component"]["hood_depth"]["v"],
        ).translate_by([0, body["height"] - body["head_l"] + 10, 0])

        self.interfaces.update(
            {
                #'front': NOTE: no front interface here
                "back": self.panel.interfaces["to_other_side"],
                "bottom": self.panel.interfaces["to_bodice"],
            }
        )

    def length(self):
        return self.panel.length()
