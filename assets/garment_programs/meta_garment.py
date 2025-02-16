import pygarment as pyg
from assets.garment_programs.bands import *
from assets.garment_programs.bands import factory as band_factory
from assets.garment_programs.bodice import *
from assets.garment_programs.bodice import factory as bodice_factory
from assets.garment_programs.bottoms import *
from assets.garment_programs.bottoms import factory as bottom_factory
from assets.garment_programs.collars import *
from assets.garment_programs.sleeves import *


class TotalLengthError(BaseException):
    """Error indicating that the total length of a garment goes beyond 
    the floor length for a given person"""
    pass

class IncorrectElementConfiguration(BaseException):
    """Error indicating that given pattern is an empty garment"""
    pass

class MetaGarment(pyg.Component):
    """Meta garment component
        Depending on parameter values it can generate sewing patterns
    for various dresses and jumpsuit styles and fit them to the body
    measurements
    """
    def __init__(self, name: str, body: dict, design: dict) -> None:
        super().__init__(name)
        self.body = body
        self.design = design

        # Elements
        self.upper_name = design['meta']['upper']['v']
        self.lower_name = design['meta']['bottom']['v']
        self.belt_name = design['meta']['wb']['v']

        # Upper garment
        if self.upper_name: 
            self.subs = [bodice_factory.build(name=self.upper_name, body=body, design=design)]

            # Set a label
            self.subs[-1].set_panel_label('body', overwrite=False)

        # Define Lower garment
        if self.lower_name:
            # NOTE: full rise for fitted tops
            Lower = bottom_factory.build(
                name=self.lower_name,
                body=body,
                design=design,
                rise=1.0 if self.upper_name and "Fitted" in self.upper_name else None,
            )
        else: 
            Lower = None

        # Belt (or not)
        # TODO Adapt the rise of the lower garment to the width of the belt for correct matching
        if self.belt_name:
            # Adjust rise to match the Lower garment if needed
            Belt = band_factory.build(
                name=self.belt_name,
                body=body,
                design=design,
                rise=Lower.get_rise() if Lower else 1.0,
            )

            self.subs.append(Belt)

            # Place below the upper garment
            if len(self.subs) > 1:
                self.subs[-1].place_by_interface(
                    self.subs[-1].interfaces['top'],
                    self.subs[-2].interfaces['bottom'], 
                    gap=5
                )

                self.stitching_rules.append(
                    (self.subs[-2].interfaces['bottom'],
                     self.subs[-1].interfaces['top']))

            # Add waist label
            self.subs[-1].interfaces['top'].edges.propagate_label('lower_interface')
            # Set panel segmentation labels
            self.subs[-1].set_panel_label('body', overwrite=False)

        # Attach Lower garment if present
        if self.lower_name:
            self.subs.append(Lower)
            # Place below the upper garment or self.wb
            if len(self.subs) > 1:
                self.subs[-1].place_by_interface(
                    self.subs[-1].interfaces['top'],
                    self.subs[-2].interfaces['bottom'], 
                    gap=5
                )
                self.stitching_rules.append(
                    (self.subs[-2].interfaces['bottom'],
                     self.subs[-1].interfaces['top']))

            # Add waist label
            if not self.belt_name:
                self.subs[-1].interfaces['top'].edges.propagate_label('lower_interface')
            # Set panel segmentation labels
            self.subs[-1].set_panel_label('leg', overwrite=False)

    def assert_total_length(self, tol=1):
        """Check the total length of components"""
        # Check that the total length of the components are less that body height
        length = self.length()
        floor = self.body['height'] - self.body['head_l']
        if length > floor + tol:
            raise TotalLengthError(f'{self.__class__.__name__}::{self.name}::ERROR:'
                                    f':Total length {length} exceeds the floor length {floor}')

    # TODO these checks don't require initialization of the pattern!
    def assert_non_empty(self, filter_belts=True):
        """Check that the garment is non-empty
            * filter_wb -- if set, then garments consisting only of waistbands are considered empty
        """
        if not self.upper_name and not self.lower_name:
            if filter_belts or not self.belt_name:
                raise IncorrectElementConfiguration()

    def assert_skirt_waistband(self):
        """Check if a generated heavy skirt is created with a waistband"""

        if self.lower_name and self.lower_name in ['SkirtCircle', 'AsymmSkirtCircle', 'SkirtManyPanels']:
            if not (self.belt_name or self.upper_name):
                raise IncorrectElementConfiguration()
