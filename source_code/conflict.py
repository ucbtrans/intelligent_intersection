#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for conflict zones
#
#######################################################################


import shapely.geometry as geom
from matplotlib.patches import Polygon
from border import cut_border_by_polygon, cut_border_by_distance


conflict_type = {
    'drive': 'v',
    'footway': 'p',
    'bicycle': 'b',
    'railway': 'r'
    }


def get_destination_bearing(g):
    """
    Get destination bearing for a guideway or crosswalk
    :param g: guideway or crosswalk dictionary
    :return: float in degrees
    """
    if 'bearing' in g:
        return g['bearing']
    else:
        return g['destination_lane']['bearing']


def get_origin_bearing(g):
    """
    Get origin bearing for a guideway or crosswalk
    :param g: guideway or crosswalk dictionary
    :return: float in degrees
    """
    if 'bearing' in g:
        return g['bearing']
    else:
        return g['origin_lane']['bearing']


def get_origin_path_id(g):
    """
    Get origin path id for a guideway or crosswalk
    :param g: guideway or crosswalk dictionary
    :return: id as an integer
    """
    if 'path_id' in g:
        path_id = g['path_id']
    else:
        path_id = g['origin_lane']['path_id']

    if type(path_id) is list:
        return path_id[-1]
    else:
        return path_id


def get_conflict_zone_type(g1, g2):
    """
    Get severity type of a conflict zone
    :param g1: guideway dictionary
    :param g2: guideway dictionary
    :return: integer 1 - 4
    """

    if g1['direction'] == 'right' or g2['direction'] == 'right':
        if g1['type'] == 'footway' or g2['type'] == 'footway':
            return 4
        return 1

    if 'meta_data' in g1:
        meta = g1['meta_data']
    else:
        meta = g1['origin_lane']['meta_data']

    if 'traffic_signals' in meta and meta['traffic_signals'] == 'yes':

        if g1['type'] == 'footway' or g2['type'] == 'footway':
            delta_angle = (get_destination_bearing(g1) - get_destination_bearing(g2) + 360.0) % 360.0
            if 225.0 < delta_angle < 315.0 or 45.0 < delta_angle < 135.0:
                return 3
            else:
                return 2

        delta_angle = (get_origin_bearing(g2) - get_origin_bearing(g1) + 360.0) % 360.0
        if 225.0 < delta_angle < 315.0 or 45.0 < delta_angle < 135.0:
            return 2
        else:
            return 3

    return 3


def get_guideway_intersection(g1, g2, polygons_dict):
    """
    Get a conflict zone as an intersection of two guideways.  
    It uses a dictionary as polygon storage to avoid double execution of intersecting polygons.
    :param g1: guideway dictionary
    :param g2: guideway dictionary
    :param polygons_dict: polygon storage dictionary
    :return: conflict zone dictionary
    """

    if g1['id'] == g2['id']:
        return None

    if get_origin_path_id(g1) == get_origin_path_id(g2):
        return None

    if g1['type'] == 'footway' and g2['type'] == 'footway':
        return None

    polygon_id1 = str(g1['id']) + '_' + str(g2['id'])
    polygon_id2 = str(g2['id']) + '_' + str(g1['id'])
    if polygon_id2 in polygons_dict:
        polygon_x = polygons_dict[polygon_id2]
    else:
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

        polygons_dict[polygon_id1] = polygon_x

    if polygon_x is None:
        return None

    median1 = geom.LineString(g1['median'])
    if median1.intersects(polygon_x):
        x = median1.intersection(polygon_x)
        if isinstance(x, geom.collection.GeometryCollection) \
                or isinstance(x, geom.multipoint.MultiPoint) \
                or isinstance(x, geom.multilinestring.MultiLineString):
            x_points = [list(y.coords)[0] for y in list(x)]
        else:
            x_points = [list(x.coords)[0]]

        min_distance = min([median1.project(geom.Point(x_point), normalized=True) for x_point in x_points])
    else:
        return None

    conflict_zone = {
        'type': str(get_conflict_zone_type(g1, g2)) + conflict_type[g1['type']] + conflict_type[g2['type']],
        'guideway1_id': g1['id'],
        'guideway2_id': g2['id'],
        'distance': min_distance,
        'polygon': polygon_x
    }
    return conflict_zone


def get_conflict_zones_per_guideway(guideway_data, all_guideways, polygons_dict):
    """
    Get a list of conflict zones for a guideway,
    It uses a dictionary as polygon storage to avoid double execution of intersecting polygons.
    :param guideway_data: guideway data dictionary
    :param all_guideways: list of all guideway data dictionaries
    :param polygons_dict: polygon storage dictionary
    :return: list of conflict zone dictionaries
    """

    conflict_zones = []
    for g in all_guideways:
        conflict_zone = get_guideway_intersection(guideway_data, g, polygons_dict)
        if conflict_zone is not None:
            conflict_zones.append(conflict_zone)

    conflict_zones.sort(key=lambda x: x['distance'])
    for i, conflict_zone in enumerate(conflict_zones):
        conflict_zone['sequence'] = i
        conflict_zone['id'] = '_'.join([str(conflict_zone[k]) for k in ['guideway1_id', 'guideway2_id', 'sequence']])

    if len(conflict_zones) > 0:
        guideway_data['reduced_median'] = cut_border_by_polygon(guideway_data['median'], conflict_zones[-1]['polygon'])
        for key in ['left_border', 'right_border']:
            border_line = geom.LineString(guideway_data[key])
            reduced_line = cut_border_by_distance(border_line,
                                                  border_line.project(geom.Point(guideway_data['reduced_median'][-1]))
                                                  )[0]
            guideway_data['reduced_' + key] = list(reduced_line.coords)

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
