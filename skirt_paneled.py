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
        self.edges = [pyp.LogicalEdge((0,0), (20, 70))]   # TODO SequentialObject?
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (55, 70)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (75, 0)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, self.edges[0].start))

        # define interface
        self.interfaces.append(pyp.InterfaceInstance(self, 0))
        self.interfaces.append(pyp.InterfaceInstance(self, 2))

        # DRAFT
        # self.interfaces.append(pyp.ConnectorEdge(self.edges[0], self.edges[0]))
        # self.interfaces.append(pyp.ConnectorEdge(self.edges[2], self.edges[2]))

class Skirt2(pyp.Component):
    """Simple 2 panel skirt"""
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)

        self.front = SkirtPanel('front')
        self.front.translate([-40, -75, 20])
        self.back = SkirtPanel('back')
        self.back.translate([-40, -75, -15])

        # TODO How the components are connected?
        # Main problem -- propagatable edge ids through the sequence of components? 
        # Knowing that the true edge ids are only known at assembly time 
        # How do I mark it on assembly for the next assembly?
        # Maybe start without the separate notion of connector edges -- add them later   

        # DRAFT ?? self.front.connect(0, self.back, 1)
        # ?? self.front.connect(1, self.back, 0)

        # TODO What is the new interface of this component? 
        # TODO use dict for interface references
        self.interfaces = [
            pyp.InterfaceInstance(self.front, 1),
            pyp.InterfaceInstance(self.back, 1)
        ]

    def assembly(self):
        base = super().assembly()

        # TODO Name collision for panels?
        # TODO Hide this type of assembly in the main class?
        front_raw = self.front()['panels']
        back_raw = self.back()['panels']
        base['pattern']['panels'] = {**front_raw, **back_raw}

        # DRAFT this is very direct, we need more nice, abstract solution
        # TODO is it good to have connectivity definition in the assembly function?
        base['pattern']['stitches'].append(pyp.connect(self.front.interfaces[0], self.back.interfaces[0]))
        base['pattern']['stitches'].append(pyp.connect(self.front.interfaces[1], self.back.interfaces[1]))

        return base   


# With waistband
class WBPanel(pyp.Panel):
    """One panel for a panel skirt"""

    def __init__(self, name) -> None:
        super().__init__(name)

        # define edge loop
        self.edges = [pyp.LogicalEdge((0,0), (0, 10))]   # TODO SequentialObject?
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (35, 10)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, (35, 0)))
        self.edges.append(pyp.LogicalEdge(self.edges[-1].end, self.edges[0].start))

        # define interface
        self.interfaces.append(pyp.InterfaceInstance(self, 0))
        self.interfaces.append(pyp.InterfaceInstance(self, 2))


class WB(pyp.Component):
    """Simple 2 panel waistband"""
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)

        self.front = WBPanel('wb_front')
        self.front.translate([-20, -2, 20])
        self.back = WBPanel('wb_back')
        self.back.translate([-20, -2, -15])

        self.interfaces = [
            pyp.InterfaceInstance(self.front, 3),
            pyp.InterfaceInstance(self.back, 3)
        ]

    def assembly(self):
        base = super().assembly()

        # TODO Name collision for panels?
        # TODO Hide this type of assembly in the main class?
        front_raw = self.front()['panels']
        back_raw = self.back()['panels']
        
        base['pattern']['panels'] = {**front_raw, **back_raw}

        # DRAFT this is very direct, we need more nice, abstract solution
        # TODO is it good to have connectivity definition in the assembly function?
        # TODO adding stitches within the connect() func
        base['pattern']['stitches'].append(pyp.connect(self.front.interfaces[0], self.back.interfaces[0]))
        base['pattern']['stitches'].append(pyp.connect(self.front.interfaces[1], self.back.interfaces[1]))

        return base   


class SkirtWB(pyp.Component):
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)

        self.wb = WB()
        self.skirt = Skirt2()


    def assembly(self):
        base = super().assembly()

        wb_raw = self.wb()
        skirt_raw = self.skirt()
        # TODO separate higher abstract fuction for putting the panels together in the assembly 
        # no need to expose all this to end user
        # Simple merge of panels
        base['pattern']['panels'] = {**wb_raw['pattern']['panels'], **skirt_raw['pattern']['panels']}

        # Simple merge of stitches
        base['pattern']['stitches'] += wb_raw['pattern']['stitches']
        base['pattern']['stitches'] += skirt_raw['pattern']['stitches']

        # TODO which edge id should be connected to which edge id? 
        base['pattern']['stitches'].append(pyp.connect(self.wb.interfaces[0], self.skirt.interfaces[0]))
        base['pattern']['stitches'].append(pyp.connect(self.wb.interfaces[1], self.skirt.interfaces[1]))

        return base   


if __name__ == '__main__':
    skirt = SkirtWB()
    pattern = skirt()

    # DEBUG 
    # print(json.dumps(pattern, indent=2, sort_keys=True))

    # Save as json file
    sys_props = Properties('./system.json')
    filename = Path(sys_props['output']) / f'{skirt.name}_{datetime.now().strftime("%y%m%d-%H-%M-%S")}.json'
    with open(filename, 'w') as f:
        json.dump(pattern, f, indent=2, sort_keys=True)
    print(f'Success! {skirt.name} saved to {filename}')