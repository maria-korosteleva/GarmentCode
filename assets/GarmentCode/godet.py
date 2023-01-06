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

class GodetSkirt(pyp.Component):
    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}')

        gdesign = design['godet-skirt']
        sk_length = gdesign['length']['v']
        ins_w = gdesign['insert_w']['v']
        ins_depth = gdesign['insert_depth']['v']

        self.front = SkirtPanel('front', ruffles=1, waist_length=body['waist'], length=sk_length, bottom_cut=0, flare=0).center_x().translate_by([0, 0, 20])
        self.back = SkirtPanel('back', ruffles=1, waist_length=body['waist'], length=sk_length, bottom_cut=0, flare=0).center_x().translate_by([0, 0, -15])

        # front and back of a skirt
        self.stitching_rules.append((self.front.interfaces[0], self.back.interfaces[0]))
        self.stitching_rules.append((self.front.interfaces[2], self.back.interfaces[2]))

        self.inserts(
            self.front, 25, ins_w, ins_depth, sk_length, 
            num_inserts=gdesign['num_inserts']['v'] / 2, 
            cuts_dist=gdesign['cuts_distance']['v'], 
            right=False)
        self.inserts(
            self.back, -20, ins_w, ins_depth, sk_length, 
            num_inserts=gdesign['num_inserts']['v'] / 2, 
            cuts_dist=gdesign['cuts_distance']['v'], 
            right=True)


    def inserts(self, panel, z_transl, ins_w, ins_depth, sk_length, num_inserts=3, cuts_dist=0, right=True):
        """Create insert panels, add cuts to the skirt panel, and connect created insert panels with them"""

        num_inserts = int(num_inserts)
        bottom_edge = panel.bottom 
        bottom_len = bottom_edge.length()

        cut_width = (bottom_len - cuts_dist * num_inserts) / num_inserts 
        if cut_width < 1:
            (f'{self.__class__.__name__}::Warning:: Cannot place {num_inserts} cuts with requested distance between cuts {cuts_dist}. Using the maximum possible distance')
            cut_width = 1  # 1 cm 
            cuts_dist = (bottom_len - cut_width * num_inserts) / num_inserts

        # Insert panels
        insert = Insert(0, width=ins_w, depth=ins_depth).translate_by([-num_inserts * ins_w / 2, -sk_length, z_transl])
        self.subs += pyp.ops.distribute_horisontally(insert, num_inserts, -ins_w, panel.name)

        # make appropriate cuts and stitches
        cut_depth = math.sqrt((ins_w / 2)**2 + ins_depth**2 - (cut_width / 2)**2)
        cut_shape = pyp.esf.from_verts([0,0], [cut_width / 2, cut_depth], [cut_width, 0])  
        for i in range(num_inserts):
            offset = cut_width / 2 + (cuts_dist / 2 if i == 0 else cuts_dist)   #  start_offest + i * stride

            new_bottom, cutted, _ = pyp.ops.cut_into_edge(cut_shape, bottom_edge, offset=offset, right=right)
            panel.edges.substitute(bottom_edge, new_bottom)
            bottom_edge = new_bottom[-1]  # New edge that needs to be cutted -- on the next step

            self.stitching_rules.append((self.subs[-1-i if right else -(num_inserts-i)].interfaces[0], pyp.Interface(panel, cutted)))
       
