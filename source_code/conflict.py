#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for conflict zones
#
#######################################################################


import shapely.geometry as geom


def get_guideway_intersection(g1, g2):
    """
    Get a conflict zone as an intersection of two guideways
    :param g1: guideway dictionary
    :param g2: guideway dictionary
    :return: conflict zone dictionary
    """

    if g1['id'] == g2['id']:
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
