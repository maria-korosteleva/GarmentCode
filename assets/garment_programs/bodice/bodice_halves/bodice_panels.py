import numpy as np

import pygarment as pyg
from assets.garment_programs.base_classes import BaseBodicePanel


class BodiceFrontHalf(BaseBodicePanel):
    def __init__(self, name: str, body: dict, design: dict) -> None:
        super().__init__(name, body, design)

        m_bust = body["bust"]
        m_waist = body["waist"]

        # sizes
        bust_point = body["bust_points"] / 2
        front_frac = (body["bust"] - body["back_width"]) / 2 / body["bust"]

        self.width = front_frac * m_bust
        waist = (m_waist - body["waist_back_width"]) / 2
        sh_tan = np.tan(np.deg2rad(body["_shoulder_incl"]))
        shoulder_incl = sh_tan * self.width
        bottom_d_width = (self.width - waist) * 2 / 3

        adjustment = sh_tan * (self.width - body["shoulder_w"] / 2)
        max_len = body["waist_over_bust_line"] - adjustment

        # side length is adjusted due to shoulder inclination
        # for the correct sleeve fitting
        fb_diff = (front_frac - (0.5 - front_frac)) * body["bust"]
        back_adjustment = sh_tan * (body["back_width"] / 2 - body["shoulder_w"] / 2)
        side_len = body["waist_line"] - back_adjustment - sh_tan * fb_diff

        self.edges.append(
            pyg.EdgeSeqFactory.from_verts(
                [0, 0],
                [-self.width, 0],
                [-self.width, max_len],
                [0, max_len + shoulder_incl],
            )
        )
        self.edges.close_loop()

        # Side dart
        bust_line = body["waist_line"] - body["_bust_line"]
        side_d_depth = 0.75 * (self.width - bust_point)  # NOTE: calculated value
        side_d_width = max_len - side_len
        s_edge, side_interface = self.add_dart(
            pyg.EdgeSeqFactory.dart_shape(side_d_width, side_d_depth),
            self.edges[1],
            offset=bust_line + side_d_width / 2,
        )
        self.edges.substitute(1, s_edge)

        # Take some fabric from the top to match the shoulder width
        s_edge[-1].end[0] += (x_upd := self.width - body["shoulder_w"] / 2)
        s_edge[-1].end[1] += sh_tan * x_upd

        # Bottom dart
        b_edge, b_interface = self.add_dart(
            pyg.EdgeSeqFactory.dart_shape(bottom_d_width, 0.9 * bust_line),
            self.edges[0],
            offset=bust_point + bottom_d_width / 2,
        )
        self.edges.substitute(0, b_edge)
        # Take some fabric from side in the bottom (!: after side dart insertion)
        b_edge[-1].end[0] = -(waist + bottom_d_width)

        # Interfaces
        self.interfaces = {
            "outside": pyg.Interface(
                self, side_interface
            ),  # side_interface,    # pyp.Interface(self, [side_interface]),  #, self.edges[-3]]),
            "inside": pyg.Interface(self, self.edges[-1]),
            "shoulder": pyg.Interface(self, self.edges[-2]),
            "bottom": pyg.Interface(self, b_interface),
            # Reference to the corner for sleeve and collar projections
            "shoulder_corner": pyg.Interface(self, [self.edges[-3], self.edges[-2]]),
            "collar_corner": pyg.Interface(self, [self.edges[-2], self.edges[-1]]),
        }

        # default placement
        self.translate_by(
            [0, body["height"] - body["head_l"] - max_len - shoulder_incl, 0]
        )


class BodiceBackHalf(BaseBodicePanel):
    """Panel for the back of basic fitted bodice block"""

    def __init__(self, name: str, body: dict, design: dict) -> None:
        super().__init__(name, body, design)

        # Overall measurements
        self.width = body["back_width"] / 2
        waist = body["waist_back_width"] / 2
        # NOTE: no inclination on the side, since there is not much to begin with
        waist_width = self.width if waist < self.width else waist
        shoulder_incl = (
            sh_tan := np.tan(np.deg2rad(body["_shoulder_incl"]))
        ) * self.width

        # Adjust to make sure length is measured from the shoulder
        # and not the de-fact side of the garment
        back_adjustment = sh_tan * (self.width - body["shoulder_w"] / 2)
        length = body["waist_line"] - back_adjustment

        # Base edge loop
        edge_0 = pyg.CurveEdgeFactory.curve_from_tangents(
            start=[0, shoulder_incl / 4],  # back a little shorter
            end=[-waist_width, 0],
            target_tan0=[-1, 0],
        )
        self.edges.append(edge_0)
        self.edges.append(
            pyg.EdgeSeqFactory.from_verts(
                edge_0.end,
                [
                    -self.width,
                    body["waist_line"] - body["_bust_line"],
                ],  # from the bottom
                [-self.width, length],
                [
                    0,
                    length + shoulder_incl,
                ],  # Add some fabric for the neck (inclination of shoulders)
            )
        )
        self.edges.close_loop()

        # Take some fabric from the top to match the shoulder width
        self.interfaces = {
            "outside": pyg.Interface(self, [self.edges[1], self.edges[2]]),
            "inside": pyg.Interface(self, self.edges[-1]),
            "shoulder": pyg.Interface(self, self.edges[-2]),
            "bottom": pyg.Interface(self, self.edges[0]),
            # Reference to the corners for sleeve and collar projections
            "shoulder_corner": pyg.Interface(
                self, pyg.EdgeSequence(self.edges[-3], self.edges[-2])
            ),
            "collar_corner": pyg.Interface(
                self, pyg.EdgeSequence(self.edges[-2], self.edges[-1])
            ),
        }

        # Bottom dart as cutout -- for straight line
        if waist < self.get_width(self.edges[2].end[1] - self.edges[2].start[1]):
            w_diff = waist_width - waist
            side_adj = (
                0 if w_diff < 4 else w_diff / 6
            )  # NOTE: don't take from sides if the difference is too small
            bottom_d_width = w_diff - side_adj
            bottom_d_width /= 2  # double darts
            bottom_d_depth = 1.0 * (length - body["_bust_line"])  # calculated value
            bottom_d_position = body["bum_points"] / 2

            # TODOLOW Avoid hardcoding for matching with the bottoms?
            dist = bottom_d_position * 0.5  # Dist between darts -> dist between centers
            b_edge, b_interface = self.add_dart(
                pyg.EdgeSeqFactory.dart_shape(bottom_d_width, 0.9 * bottom_d_depth),
                self.edges[0],
                offset=bottom_d_position
                + dist / 2
                + bottom_d_width
                + bottom_d_width / 2,
            )
            b_edge, b_interface = self.add_dart(
                pyg.EdgeSeqFactory.dart_shape(bottom_d_width, bottom_d_depth),
                b_edge[0],
                offset=bottom_d_position - dist / 2 + bottom_d_width / 2,
                edge_seq=b_edge,
                int_edge_seq=b_interface,
            )

            self.edges.substitute(0, b_edge)
            self.interfaces["bottom"] = pyg.Interface(self, b_interface)

            # Remove fabric from the sides if the diff is big enough
            b_edge[-1].end[0] += side_adj

        # default placement
        self.translate_by(
            [0, body["height"] - body["head_l"] - length - shoulder_incl, 0]
        )

    def get_width(self, level):
        return self.width
