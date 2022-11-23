import json
from pathlib import Path
from datetime import datetime

# Custom
import pypattern as pyp
from customconfig import Properties

class SkirtPanel(pyp.Panel):
    """One panel for a panel skirt"""

    def __init__(self, name) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = [pyp.Edge((0,0), (20, 70))]   # TODO SequentialObject?
        self.edges.append(pyp.Edge(self.edges[-1].end, (55, 70)))
        self.edges.append(pyp.Edge(self.edges[-1].end, (75, 0)))
        self.edges.append(pyp.Edge(self.edges[-1].end, self.edges[0].start))

        # define interface
        self.interfaces.append(pyp.ConnectorEdge(self.edges[0], self.edges[0]))
        self.interfaces.append(pyp.ConnectorEdge(self.edges[2], self.edges[2]))

class Skirt2(pyp.Component):
    """Simple 2 panel skirt"""
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)

        self.front = SkirtPanel('front')
        self.front.translate([-40, -75, 20])
        self.back = SkirtPanel('back')
        self.back.translate([-40, -75, -15])

        # TODO How the components are connected?

        # DRAFT ?? self.front.connect(0, self.back, 1)
        # ?? self.front.connect(1, self.back, 0)

        # TODO What is the new interface of this component? 

        # Main problem -- propagatable edge ids through the sequence of components? 
        # Knowing that the true edge ids are only known at assembly time 

    def assembly(self):
        base = super().assembly()

        # TODO Name collision for panels?
        # TODO Hide this type of assembly in the main class?
        front_raw = self.front()['panels']
        back_raw = self.back()['panels']
        base['pattern']['panels'] = {**front_raw, **back_raw}

        # DRAFT this is very direct, we need more nice, abstract solution
        # TODO is it good to have connectivity definition in the assembly function?
        base['pattern']['stitches'].append(pyp.stitch(front_raw, 0, back_raw, 0))
        base['pattern']['stitches'].append(pyp.stitch(front_raw, 1, back_raw, 1))

        return base   


if __name__ == '__main__':
    skirt = Skirt2()
    pattern = skirt()

    print(json.dumps(pattern, indent=2, sort_keys=True))

    # Save as json file
    sys_props = Properties('./system.json')
    with open(Path(sys_props['output']) / f'skirt2_st_{datetime.now().strftime("%y%m%d-%H-%M-%S")}.json', 'w') as f:
        json.dump(pattern, f, indent=2, sort_keys=True)