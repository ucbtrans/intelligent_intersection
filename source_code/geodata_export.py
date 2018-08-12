"""
Routines for intersection data export.

Supported data formats:
    + KML

API:
    + export_guideways_kml()

"""

import sys
import logging
import numpy as np
import scipy.ndimage as ndimage
import matplotlib.pyplot as plt
from kml_routines import KML



logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    stream=sys.stdout,
                    #filename='mylog.log',
                    filemode='w+')



#==============================================================================
# Auxiliary functions
#==============================================================================






#==============================================================================
# API
#==============================================================================

def export_guideways_kml(args):
    '''
    Export guideways to a KML file.

    :param args:
        Dictionary with function arguments:
            args['kmlfile'] = Path to KML file that needs to be generated.
            args['guideways'] = List of guideways.
            args['crosswalks'] = (Optional) List of crosswalks.
            args['properties'] = (Optional) Dictionary describing how each type of guideways should be exported:
                args['properties'][<type>]['color'] = Color in the form "TTBBGGRR".
                args['properties'][<type>]['median'] = Boolean indicator whether to show just a guideway's median (if True),
                                                       or a full polygon describing guideway.
                args['properties'][<type>]['width'] = Line width. This parameter is only relevant if we display medians.
                                 Admissible guideway types are:
                                    + 'drive' - vehicle guideway;
                                    + 'bicycle' - bicycle guideway;
                                    + 'rail' - rail guideway;
                                    + 'crosswalk' - pedestrian gudeway.
            args['debug'] = (Optional) Boolean parameter indicating whether DEBUG info must be logged.

    :returns res:
        True if operation was successful, False - otherwise.
    '''

    if args == None:
        return False

    kmlfile = args['kmlfile']
    guideways = args['guideways']

    crosswalks = []
    if 'crosswalks' in args.keys():
        crosswalks = args['crosswalks']

    properties = dict()
    properties['drive'] = {'color': "FFDD0000", 'median': True, 'width': 3}
    properties['bicycle'] = {'color': "FF00DD00", 'median': True, 'width': 3}
    properties['rail'] = {'color': "FF00BBBB", 'median': True, 'width': 3}
    properties['crosswalk'] = {'color': "FF0000BB", 'median': True, 'width': 3}
    if 'properties' in args.keys():
        props = args['properties']
        if 'drive' in props.keys():
            if 'color' in props['drive'].keys():
                properties['drive']['color'] = props['drive']['color']
            if 'median' in props['drive'].keys():
                properties['drive']['median'] = props['drive']['median']
            if 'width' in props['drive'].keys():
                properties['drive']['width'] = props['drive']['width']
        if 'bicycle' in props.keys():
            if 'color' in props['drive'].keys():
                properties['drive']['color'] = props['drive']['color']
            if 'median' in props['drive'].keys():
                properties['drive']['median'] = props['drive']['median']
            if 'width' in props['drive'].keys():
                properties['drive']['width'] = props['drive']['width']
        if 'rail' in props.keys():
            if 'color' in props['drive'].keys():
                properties['drive']['color'] = props['drive']['color']
            if 'median' in props['drive'].keys():
                properties['drive']['median'] = props['drive']['median']
            if 'width' in props['drive'].keys():
                properties['drive']['width'] = props['drive']['width']
        if 'crosswalk' in props.keys():
            if 'color' in props['drive'].keys():
                properties['drive']['color'] = props['drive']['color']
            if 'median' in props['drive'].keys():
                properties['drive']['median'] = props['drive']['median']
            if 'width' in props['drive'].keys():
                properties['drive']['width'] = props['drive']['width']

    debug = False
    if 'debug' in args.keys():
        debug = args['debug']

    my_kml = KML()

    list_vw, list_bw, list_rw = [], [], []
    for gw in guideways:
        if gw['type'] == 'drive':
            list_vw.append(gw)
        if gw['type'] == 'bicycle':
            list_bw.append(gw)
        if gw['type'] == 'railway':
            list_rw.append(gw)

    if len(list_vw) > 0:
        if properties['drive']['median']:
            my_kml.guideway_medians(list_vw, color=properties['drive']['color'], width=properties['drive']['width'])
        else:
            my_kml.guideways(list_vw, color=properties['drive']['color'])

    if len(list_bw) > 0:
        if properties['bicycle']['median']:
            my_kml.guideway_medians(list_bw, color=properties['bicycle']['color'], width=properties['bicycle']['width'])
        else:
            my_kml.guideways(list_bw, color=properties['bicycle']['color'])

    if len(list_rw) > 0:
        if properties['rail']['median']:
            my_kml.guideway_medians(list_rw, color=properties['rail']['color'], width=properties['rail']['width'])
        else:
            my_kml.guideways(list_rw, color=properties['rail']['color'])

    if len(crosswalks) > 0:
        if properties['crosswalk']['median']:
            my_kml.crosswalk_medians(crosswalks, color=properties['crosswalk']['color'], width=properties['crosswalk']['width'])
        else:
            my_kml.crosswalks(crosswalks, color=properties['crosswalk']['color'])

    my_kml.save(kmlfile)

    return True


def export_traces_kml(args):
    '''
    Export traces to a KML file.

    :param args:
        Dictionary with function arguments:
            args['kmlfile'] = Path to KML file that needs to be generated.
            args['traces'] = List of traces: [[(lon, lat)...(lon, lat)]].
            args['color'] = (Optional) Color in the form "TTBBGGRR". Default = "FF999999".
            args['width'] = (Optional) Line width. Default = 2.
            args['latlon'] = (Optional) Specifies how coordinates are given If true, then we read (lat, lon). Default = False.
            args['debug'] = (Optional) Boolean parameter indicating whether DEBUG info must be logged.

    :returns res:
        True if operation was successful, False - otherwise.
    '''

    if args == None:
        return False

    kmlfile = args['kmlfile']
    traces = args['traces']

    width = 2
    if 'width' in args.keys():
        width = args['width']

    color = "FF999999"
    if 'color' in args.keys():
        color = args['color']

    latlon = False
    if 'latlon' in args.keys():
        latlon = args['latlon']

    debug = False
    if 'debug' in args.keys():
        debug = args['debug']

    my_kml = KML()
    my_kml.traces(traces, latlon=latlon, color=color, width=width)
    my_kml.save(kmlfile)

    return True









#==============================================================================
# Main function - for standalone execution.
#==============================================================================

def main(argv):
    print(__doc__)
    




if __name__ == "__main__":
    main(sys.argv)