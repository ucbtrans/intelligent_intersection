#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module calculates blind zones
#
#######################################################################


import shapely.geometry as geom
from border import get_compass, get_distance_between_points
import nvector as nv


nv_frame = nv.FrameE(a=6371e3, f=0)


def get_sector(point, block):
    """
    Get visibility sector from a point to a blocking object
    :param point: point coordinates
    :param block: guideway dictionary
    :return: max and min azimuths and points where sector boundaries crosses the block
    """
    max_azimuth = -1.0
    min_azimuth = 361.0
    for x in block['reduced_left_border'] + block['reduced_right_border']:
        azimuth = get_compass(point, x)

        if azimuth < min_azimuth:
            min_point = x
            min_azimuth = azimuth
        elif azimuth == min_azimuth:
            if get_distance_between_points(point, x) < get_distance_between_points(point, min_point):
                min_point = x
                min_azimuth = azimuth

        if azimuth > max_azimuth:
            max_point = x
            max_azimuth = azimuth
        elif azimuth == max_azimuth:
            if get_distance_between_points(point, x) < get_distance_between_points(point, max_point):
                max_point = x
                max_azimuth = azimuth

    return min_azimuth, max_azimuth, min_point, max_point


def get_point_by_azimuth(point, azimuth, distance=1000.0):
    pt = nv_frame.GeoPoint(latitude=point[1], longitude=point[0], degrees=True)
    result, _azimuthb = pt.geo_point(distance=distance, azimuth=azimuth, degrees=True)
    return result.longitude_deg, result.latitude_deg


def iz_azimuth_in_the_shadow(point, border, azimuth=0.0):
    return geom.LineString(border).intersects(geom.LineString([point, get_point_by_azimuth(point, azimuth)]))


def get_sector_polygon(point, blocking_guideway):
    min_azimuth, max_azimuth, min_point, max_point = get_sector(point, blocking_guideway)

    bissectrice = (min_azimuth + max_azimuth)/2.0
    if iz_azimuth_in_the_shadow(point, blocking_guideway['median']):
        # Azimuth at 0 degrees is in the shadow.  Invert the bissectrice direction
        bissectrice = (bissectrice + 180.0) % 360.0

    return geom.Polygon([point,
                         min_point,
                         get_point_by_azimuth(point, min_azimuth),
                         get_point_by_azimuth(point, bissectrice),
                         get_point_by_azimuth(point, max_azimuth),
                         max_point
                         ]
                        )


def get_shadow_polygon(point, block):
    """
    Get a sector defined by a point and a blocking object.  Assuming that a source of light is located at the point.
    Then split the sector into two pieces: one that is closer to the point and therefore not in the shadow,
    and another one that is behind the block and is in the shadow. 
    The split gets obtained by subtracting the block polygon from the sector.
    The shadow piece gets identified by having the largest area versus other pieces.
    Return a polygon representing the are shadow area.
    :param point: point coordinates
    :param block: guideway dictionary
    :return: polygon
    """
    block_polygon = geom.Polygon(block['left_border'] + block['right_border'][::-1])
    sector_polygon = get_sector_polygon(point, block)

    if sector_polygon.intersects(block_polygon):
        polygons = list(sector_polygon.difference(block_polygon))
        polygons.sort(key=lambda x: x.area)
        return polygons[-1]
    else:
        # Something went terribly wrong
        return None


def get_shadow(point, blocking_guideway, shadowed_guideway):
    polygon = geom.Polygon(shadowed_guideway['left_border'] + shadowed_guideway['right_border'][::-1])
    shadow_polygon = get_shadow_polygon(point, blocking_guideway)
    if shadow_polygon is not None and polygon.intersects(shadow_polygon):
        return polygon.intersection(shadow_polygon)
    else:
        return None


def get_shadows(point, all_guidways, shadowed_guideway):
    result = None
    for g in all_guidways:
        if g['type'] == 'bicycle' or g['type'] == 'footway' or g['id'] == shadowed_guideway['id']:
            continue
        p = get_shadow(point, g, shadowed_guideway)
        if p is not None:
            if result is None:
                result = p
            else:
                result = result.union(p)
    return result


def normalized_to_geo(point, conflict_zone, guideway_data):
    return point
