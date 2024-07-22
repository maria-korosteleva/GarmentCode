"""Design analysis routines to supply intresting stats"""

import pygarment.pattern.core as pattern
import yaml

# panels
def count_panels(pattern:pattern.BasicPattern, props, verbose=False):
    
    n_panels = len(pattern.pattern['panels'].keys())
    if verbose:
        print(pattern.name, ' Panel count ', n_panels)

    props['generator']['stats']['panel_count'][pattern.name] = n_panels


# Type determination

def bottom_length(design):
    meta = design['meta']
    if meta['bottom']['v']:
        bottom_section = None
        if meta['bottom']['v'] in ['SkirtCircle', 'AsymmSkirtCircle', 'SkirtManyPanels']:
            bottom_section = 'flare-skirt'
        elif meta['bottom']['v'] == 'Pants':
            bottom_section = 'pants'
        elif meta['bottom']['v'] == 'Skirt2':
            bottom_section = 'skirt'
        elif meta['bottom']['v'] == 'PencilSkirt':
            bottom_section = 'pencil-skirt'
        elif meta['bottom']['v'] == 'SkirtLevels':
            bottom_section = 'levels-skirt'
        elif meta['bottom']['v'] == 'GodetSkirt':
            base = design['godet-skirt']['base']['v']
            if base == 'Skirt2':
                bottom_section = 'skirt'
            else: # One other option
                bottom_section = 'pencil-skirt'
        else:
            raise(ValueError(f'Unknown bottoms type {meta["bottom"]["v"]}'))

        return design[bottom_section]['length']['v']
    else:
        return 0

def sleeve_length(design):
    # Sleeve length
    sleeve_len_r = design['sleeve']['length']['v'] if not design['sleeve']['sleeveless']['v'] else 0
    sleeve_len_l = design['left']['sleeve']['length']['v'] if design['left']['enable_asym']['v'] and not design['left']['sleeve']['sleeveless']['v'] else 0
    return max(sleeve_len_r, sleeve_len_l) 

def top_length(design):
    if design['meta']['upper']['v'] == 'FittedShirt':
        return 1.
    elif design['meta']['upper']['v'] == 'Shirt':
        return design['shirt']['length']['v']
    else:
        return 0.

def vertical_len(design):
    # NOTE: this will give very approximate result since 
    # the units of mesurement are slightly different
    wb_len = design['waistband']['width']['v'] if design['meta']['wb']['v'] else 0
    return top_length(design) + wb_len + bottom_length(design)

def garment_type(el_name, design, props, verbose=False):
    main_type = None
    add_types = []
    # Main:
    # + upper garment (short skirt - top or dress?)
    # + skirt
    # + pants
    # + dress
    # + jumpsuit
    # Additional labels:
    # + asymmetrical top
    # + Hoody?
    # + maxi/midi/mini
    # + sleeve/less
    # + long sleeve / short sleeve? 
    meta = design['meta']
    if meta['upper']['v']: 
        if meta['bottom']['v'] and 'Pants' in meta['bottom']['v']:
            main_type = 'jumpsuit'  
        elif vertical_len(design) < 1.4:  # NOTE: very approximate division
            main_type = 'upper_garment'
        else: 
            main_type = 'dress'
    else:
        if 'Pants' in meta['bottom']['v']:
            main_type = 'pants'  
        else:
            main_type = 'skirt'
    
    # Additional types
    if meta['upper']['v']:
        if design['left']['enable_asym']['v']:
            add_types.append('asymmetric_top')
        if (not design['left']['enable_asym']['v'] 
                and design['collar']['component']['style']['v']
                and 'Hood' in design['collar']['component']['style']['v']):
            add_types.append('hoodie')
        
        if (design['sleeve']['sleeveless']['v'] 
                and (design['left']['sleeve']['sleeveless']['v'] if design['left']['enable_asym']['v'] else True)):
            add_types.append('sleeveless')
        else:
            add_types.append('with_sleeves')

            sleeve_len = sleeve_length(design)
            if sleeve_len < 0.5:
                add_types.append('short_sleeve')
            else:
                add_types.append('long_sleeve')
    
    # Mini/Midi/Maxi
    if meta['bottom']['v']:
        length = bottom_length(design)
        if length < 0.3:
            add_types.append('mini')
        elif length < 0.5:
            add_types.append('knee_len')
        elif length < 0.65:
            add_types.append('midi')
        else:
            add_types.append('maxi')


    if verbose:
        print(el_name, ' types ', main_type, add_types)

    props['generator']['stats']['garment_types'][el_name] = {
        'main': main_type,
        'styles': add_types
    }

    # Summary 
    summary = props['generator']['stats']['garment_types_summary']
    if main_type not in summary['main']:
        summary['main'][main_type] = 1
    else:
        summary['main'][main_type] += 1
    for style_t in add_types:
        if style_t not in summary['style']:
            summary['style'][style_t] = {'total': 0}
        summary['style'][style_t]['total'] += 1
        if main_type not in summary['style'][style_t]:
            summary['style'][style_t][main_type] = 1
        else:
            summary['style'][style_t][main_type] += 1
 