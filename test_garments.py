
from datetime import datetime
from pathlib import Path

# Custom
from customconfig import Properties
from assets.GarmentCode.skirt_paneled import *
from assets.GarmentCode.tee import *
from assets.GarmentCode.godet import *

if __name__ == '__main__':

    test_garments = [
        # SkirtWB(1),
        # SkirtWB(1.5, 0),
        # SkirtWB(2, 0),
        # SkirtWB(2),
        # WB(),
        # Skirt2(),
        # SkirtManyPanels(n_panels=2),
        # SkirtManyPanels(n_panels=4),
        # SkirtManyPanels(n_panels=10),
        # TShirt(),
        # TShirt(ruffle_sleeve=True),
        # FittedTShirt(),
        GodetSkirt(40, 50)
    ]

    # test_garments[0].translate_by([2, 0, 0])

    for piece in test_garments:
        pattern = piece()

        # DEBUG 
        # print(json.dumps(pattern, indent=2, sort_keys=True))

        # Save as json file
        sys_props = Properties('./system.json')
        filename = pattern.serialize(
            Path(sys_props['output']), 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=False)

        print(f'Success! {piece.name} saved to {filename}')