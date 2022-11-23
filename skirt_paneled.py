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



class Skirt2(pyp.Component):
    """Simple 2 panel skirt"""
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)

        self.front = SkirtPanel('front')
        self.front.translate([-40, -75, 10])
        self.back = SkirtPanel('back')
        self.back.translate([-40, -75, -10])

    def assembly(self):
        base = super().assembly()

        # TODO add stitches?

        # TODO Name collision for panels?
        # TODO Hide this type of assembly in the main class?
        base['pattern']['panels'] = {**self.front()['panels'], **self.back()['panels']}

        return base   


if __name__ == '__main__':
    skirt = Skirt2()
    pattern = skirt()

    print(json.dumps(pattern, indent=2, sort_keys=True))

    # Save as json file
    sys_props = Properties('./system.json')
    with open(Path(sys_props['output']) / f'skirt2_{datetime.now().strftime("%y%m%d-%H-%M-%S")}.json', 'w') as f:
        json.dump(pattern, f, indent=2, sort_keys=True)