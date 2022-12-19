import math

# Custom
import pypattern as pyp
from .skirt_paneled import SkirtPanel


class Insert(pyp.Panel):
    def __init__(self, id, width=30, depth=30) -> None:
        super().__init__(f'Insert_{id}')

        self.edges = pyp.esf.from_verts([0, 0], [width/2, depth], [width, 0], loop=True)

        self.interfaces = [
            pyp.Interface(self, self.edges[:2])
        ]

        print(self.interfaces[-1])  # DEBUG

class GodetSkirt(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}')

        sk_length = design['skirt']['length']['v']
        ins_w = design['godet-skirt']['insert_w']['v']
        ins_depth = design['godet-skirt']['insert_depth']['v']

        self.front = SkirtPanel('front', ruffles=1, length=sk_length, bottom_cut=0).center_x().translate_by([0, 0, 20])
        self.back = SkirtPanel('back', ruffles=1, length=sk_length, bottom_cut=0).center_x().translate_by([0, 0, -15])

        # front and back of a skirt
        self.stitching_rules.append((self.front.interfaces[0], self.back.interfaces[0]))
        self.stitching_rules.append((self.front.interfaces[2], self.back.interfaces[2]))

        self.inserts(self.front, 25, ins_w, ins_depth, sk_length, right=False)
        self.inserts(self.back, -20, ins_w, ins_depth, sk_length, right=True)


    def inserts(self, panel, z_transl, ins_w, ins_depth, sk_length, right=True):

        # Inserts for front of the skirt
        insert = Insert(0, width=ins_w, depth=ins_depth).translate_by([-35, -sk_length, z_transl])

        cut_depth = math.sqrt((ins_w / 2)**2 + ins_depth**2 - (ins_w/4)**2)
        cut = pyp.esf.from_verts([0,0], [ins_w / 4, cut_depth], [ins_w / 2, 0])  # TODO width cut is also a parameter

        self.subs += pyp.ops.distribute_horisontally(insert, 3, -ins_w, panel.name)

        # make appropriate cuts and stitches
        bottom_edge = panel.bottom 
        for i in range(3):
            # TODO Offset specification should make more sense
            # TODO determining orientation is not obvious due to normal swaps..

            offset =  0.14 + i * 0.1   # 0.14 + (2 - i) * 0.1 0.16 + (2 - i) * 0.1 if right else
            new_bottom, cutted = pyp.ops.cut_into_edge(cut, bottom_edge, offset=offset, right=right)
            panel.edges.substitute(bottom_edge, new_bottom)
            bottom_edge = new_bottom[-1]# OR front?   new_bottom[0] if right else 

            self.stitching_rules.append((self.subs[-1-i if right else -(3-i)].interfaces[0], pyp.Interface(panel, cutted)))
       
