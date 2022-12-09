import math

# Custom
import pypattern as pyp
from .skirt_paneled import RuffleSkirtPanel


class Insert(pyp.Panel):
    def __init__(self, id, width=30, depth=30) -> None:
        super().__init__(f'Insert_{id}')

        self.edges = pyp.EdgeSequence.from_verts([0, 0], [width/2, depth], [width, 0], loop=True)

        self.interfaces = [
            pyp.Interface(self, self.edges[:2])
        ]

        print(self.interfaces[-1])  # DEBUG

class GodetSkirt(pyp.Component):
    def __init__(self, ins_w=30, ins_depth=20, sk_length=70) -> None:
        super().__init__(f'{self.__class__.__name__}')

        self.front = RuffleSkirtPanel('front', ruffles=1, length=sk_length, bottom_cut=2).center_x().translate_by([0, 0, 20])
        self.back = RuffleSkirtPanel('back', ruffles=1, length=sk_length, bottom_cut=2).center_x().translate_by([0, 0, -15])

        # Try inserts
        self.test_insert = Insert(0, width=ins_w, depth=ins_depth).center_x().translate_by([0, -sk_length, 25])

        cut_depth = math.sqrt((ins_w / 2)**2 + ins_depth**2 - (ins_w/4)**2)
        cut = pyp.EdgeSequence.from_verts([0,0], [ins_w / 4, cut_depth], [ins_w / 2, 0])  # TODO width cut is also a parameter

        edge_id = 0
        # TODO Offset should make more sense
        # TODO determining orientation is not obvious due to normal swaps..
        new_bottom, cutted = pyp.ops.cut_into_edge(cut, self.front.edges[0], offset=0.4, right=False)
        self.front.edges.substitute(edge_id, new_bottom)

        self.stitching_rules = pyp.Stitches(
            (self.test_insert.interfaces[0], pyp.Interface(self.front, cutted)),
            (self.front.interfaces[0], self.back.interfaces[0]),
            (self.front.interfaces[2], self.back.interfaces[2])
        )
