#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for conflict zones
#
#######################################################################


import shapely.geometry as geom
from matplotlib.patches import Polygon


conflict_type = {
    'drive': 'v',
    'footway': 'p',
    'bicycle': 'b',
    'railway': 'r'
    }


def get_conflict_zone_type(g1, g2):
    """
    Get severity type of a conflict zone
    :param g1: guideway dictionary
    :param g2: guideway dictionary
    :return: integer 1 - 3
    """

    if g1['direction'] == 'right' or g2['direction'] == 'right':
        return 1

    if 'meta_data' in g1:
        meta = g1['meta_data']
    else:
        meta = g1['origin_lane']['meta_data']

    if 'traffic_signal' in meta and meta['traffic_signals'] == 'yes':

        if g1['type'] == 'footway' or g2['type'] == 'footway':
            return 2

        delta_angle = (g2['origin']['bearing'] - g1['origin']['bearing'] + 360) % 360
        if delta_angle > 225.0 or delta_angle < 135.0:
                return 2

    return 3


def get_guideway_intersection(g1, g2):
    """
    Get a conflict zone as an intersection of two guideways
    :param g1: guideway dictionary
    :param g2: guideway dictionary
    :return: conflict zone dictionary
    """

    if g1['id'] == g2['id']:
        return None

    if g1['type'] == 'footway' and g2['type'] == 'footway':
        return None

    median1 = geom.LineString(g1['median'])
    median2 = geom.LineString(g2['median'])

    if not median1.intersects(median2):
        return None

    x = median1.intersection(median2)

    if isinstance(x, geom.collection.GeometryCollection) \
            or isinstance(x, geom.multipoint.MultiPoint) \
            or isinstance(x, geom.multilinestring.MultiLineString):
        x_points = [list(y.coords)[0] for y in list(x)]
    else:
        x_points = [list(x.coords)[0]]

    min_distance = min([median1.project(geom.Point(x_point), normalized=True) for x_point in x_points])

    polygon1 = geom.Polygon(g1['left_border'] + g1['right_border'][::-1])
    polygon2 = geom.Polygon(g2['left_border'] + g2['right_border'][::-1])

    if not polygon1.is_valid:
        polygon1 = polygon1.buffer(0)

    if not polygon2.is_valid:
        polygon2 = polygon2.buffer(0)

    if polygon1.intersects(polygon2):
        polygon_x = polygon1.intersection(polygon2)
    else:
        polygon_x = None

    conflict_zone = {
        'type': str(get_conflict_zone_type(g1, g2)) + conflict_type[g1['type']] + conflict_type[g2['type']],
        'guideway1_id': g1['id'],
        'guideway2_id': g2['id'],
        'distance': min_distance,
        'polygon': polygon_x
    }
    return conflict_zone


def get_conflict_zones_per_guideway(guideway_data, all_guideways):
    """
    Get a list of conflict zones for a guideway
    :param guideway_data: guideway data dictionary
    :param all_guideways: list of all guideway data dictionaries
    :return: list of conflict zone dictionaries
    """

    conflict_zones = []
    for g in all_guideways:
        conflict_zone = get_guideway_intersection(guideway_data, g)
        if conflict_zone is not None:
            conflict_zones.append(conflict_zone)

    conflict_zones.sort(key=lambda x: x['distance'])
    for i, conflict_zone in enumerate(conflict_zones):
        conflict_zone['sequence'] = i
        conflict_zone['id'] = '_'.join([str(conflict_zone[k]) for k in ['guideway1_id', 'guideway2_id', 'sequence']])

    return conflict_zones


def get_polygon_from_conflict_zone(shapely_polygon,
                                   fc='#FF9933',
                                   ec='w',
                                   alpha=0.8,
                                   linestyle='solid',
                                   joinstyle='round'
                                   ):
    """
    Get a polygon from a conflict zone
    :param shapely_polygon: Polygon (a Shapely object)
    :param fc: foreground color
    :param ec: edge color
    :param alpha: transparency
    :param linestyle: line style
    :param joinstyle: smoothing of joining lines
    :return: polygon (a MatPlotLib object)
    """

    return Polygon(list(geom.mapping(shapely_polygon)['coordinates'][0]),
                   closed=True,
                   fc=fc,
                   ec=ec,
                   alpha=alpha,
                   linestyle=linestyle,
                   joinstyle=joinstyle
                   )


def plot_conflict_zone(conflict_zone,
                       fig=None,
                       ax=None,
                       alpha=0.8,
                       fc='#FF9933',
                       ec='w'
                       ):
    """
    Plot a conflict zone
    :param conflict_zone: dictionary
    :param fig: MatPlotLib figure
    :param ax: MatPlotLib plot
    :param alpha: transparency
    :param fc: foreground color
    :param ec: edge color
    :return: a tuple of a MatPlotLib image and plot
    """

    if fig is None or ax is None:
        return None, None

    if isinstance(conflict_zone['polygon'], geom.multipolygon.MultiPolygon):
        polygons = list(conflict_zone['polygon'])
    else:
        polygons = [conflict_zone['polygon']]

    for polygon in polygons:
        ax.add_patch(get_polygon_from_conflict_zone(polygon, alpha=alpha, fc=fc, ec=ec))

    return fig, ax


def plot_conflict_zones(conflict_zones,
                       fig=None,
                       ax=None,
                       alpha=0.8,
                       fc='#FF9933',
                       ec='w'
                       ):
    """
    Plot a list of conflict zones
    :param conflict_zones: list of dictionaries
    :param fig: MatPlotLib figure
    :param ax: MatPlotLib plot
    :param alpha: transparency
    :param fc: foreground color
    :param ec: edge color
    :return: a tuple of a MatPlotLib image and plot
    """

    for conflict_zone in conflict_zones:
        fig, ax = plot_conflict_zone(conflict_zone, fig=fig, ax=ax, alpha=alpha, fc=fc, ec=ec)

    return fig, ax
