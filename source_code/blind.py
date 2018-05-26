#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module calculates blind zones
#
#######################################################################


import shapely.geometry as geom
from matplotlib.patches import Polygon
from guideway import get_polygon_from_guideway
from border import get_compass, get_distance_between_points, get_closest_point, cut_border_by_polygon,\
    polygon_within_box
import nvector as nv
from log import get_logger, dictionary_to_log


logger = get_logger()
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


def get_point_by_azimuth(point, azimuth, distance=100000.0):
    pt = nv_frame.GeoPoint(latitude=point[1], longitude=point[0], degrees=True)
    result, _azimuthb = pt.geo_point(distance=distance, azimuth=azimuth, degrees=True)
    return result.longitude_deg, result.latitude_deg


def iz_azimuth_in_the_shadow(point, border, azimuth=0.0):
    return geom.LineString(border).intersects(geom.LineString([point, get_point_by_azimuth(point, azimuth)]))


def get_sector_polygon(point, block):
    min_azimuth, max_azimuth, min_point, max_point = get_sector(point, block)

    bissectrice = (min_azimuth + max_azimuth)/2.0
    if not iz_azimuth_in_the_shadow(point, block['reduced_left_border'], azimuth=bissectrice):
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


def combine_sector_polygons(point, block):
    polygon = None
    polygons = []
    if 'reduced_left_border' not in block:
        return None
    pt0 = block['reduced_left_border'][0]
    for pt1 in (block['reduced_left_border'] + block['reduced_right_border'])[1:]:
        temp_block = {'reduced_left_border':[pt0,pt1], 'median':block['median'], 'reduced_right_border': []}
        pol = get_sector_polygon(point, temp_block)
        pt0 = pt1
        if not isinstance(pol, geom.polygon.Polygon):
            continue
        if not pol.is_valid:
            pol = pol.buffer(0)
        if polygon is None:
            polygon = pol
        else:
            try:
                polygon = polygon.union(pol)
            except Exception as e:
                logger.exception("Block Id: %d, type: %s, sector type: %s" % (block['id'], type(pol), type(polygon)))
                logger.exception(e)
                polygons.append(pol)
                continue

    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    return polygon


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
    if not block_polygon.is_valid:
        block_polygon = block_polygon.buffer(0)
    sector_polygon = combine_sector_polygons(point, block)
    if sector_polygon is None:
        return None

    if sector_polygon.intersects(block_polygon):
        try:
            polygons = list(sector_polygon.difference(block_polygon))
        except Exception as e:
            logger.exception("Block Id: %d. Can not intersect with the sector" % block['id'])
            logger.exception(e)
            return sector_polygon
        polygons.sort(key=lambda x: x.area)
        return polygons[-1]
    else:
        logger.error("Block Id: %d. Something went terribly wrong" % block['id'])
        return None


def get_shadow(point, blocking_guideway, shadowed_guideway):
    polygon = geom.Polygon(shadowed_guideway['left_border'] + shadowed_guideway['right_border'][::-1])
    if not polygon.is_valid:
        polygon = polygon.buffer(0)
    shadow_polygon = get_shadow_polygon(point, blocking_guideway)
    if shadow_polygon is not None and polygon.intersects(shadow_polygon):
        x = polygon.intersection(shadow_polygon)
        if isinstance(x, geom.polygon.Polygon):
            return x
        elif isinstance(x, geom.multipolygon.MultiPolygon):
            return x
        return None
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


def normalized_to_geo(point_of_view, guideway_data, conflict_zone=None):
    """
    Convert normalized coordinates (between 0 and 1) to lon and lat.
    point[0] is relative distance from the beginning of the median to the intersection with the conflict zone.
    point[1] is position within the width of the guideway, 
    where 0.5 is on the median, 0 on the left border and 1 on the right border.
    :param point_of_view: a tuple of floats between 0 and 1
    :param conflict_zone: conflict zone dictionary
    :param guideway_data: guideway dictionary
    :return: a tuple of lon and lat
    """

    if point_of_view[0] < 0:
        return guideway_data['median'][0]
    elif point_of_view[0] > 1.0:
        return guideway_data['median'][-1]

    if point_of_view[0] < 0.0001:
        x = 0.0001
    elif point_of_view[0] > 0.9999:
        x = 0.9999
    else:
        x = point_of_view[0]

    point = (x, point_of_view[1])

    if conflict_zone is None:
        shortened_median = guideway_data['median']
    else:
        shortened_median = cut_border_by_polygon(guideway_data['median'], conflict_zone['polygon'], multi_string_index=0)
    if shortened_median is None:
        return None

    point_on_median = geom.LineString(shortened_median).interpolate(point[0], normalized=True).coords[0]
    point_on_left_border = get_closest_point(point_on_median, guideway_data['left_border'])
    point_on_right_border = get_closest_point(point_on_median, guideway_data['right_border'])

    if point[1] < 0:
        return point_on_left_border
    elif point[1] > 1.0:
        return point_on_right_border
    elif point[1] == 0.5:
        return point_on_median
    else:
        cross_line = geom.LineString([point_on_left_border, point_on_median, point_on_right_border])
        return cross_line.interpolate(point[1], normalized=True).coords[0]


def get_blind_zone_data(point, current_guideway, conflict_zone, blocking_guideways):

    if conflict_zone['guideway1_id'] != current_guideway['id']:
        return None

    point_of_view = normalized_to_geo(point, current_guideway, conflict_zone)
    blind_zone_polygon = get_shadows(point_of_view, blocking_guideways, current_guideway)

    blind_zone_data = {'point': point,
                       'guideway_id': current_guideway['id'],
                       'conflict_zone': conflict_zone,
                       'blocking_ids': [g['id'] for g in blocking_guideways],
                       'polygon': blind_zone_polygon
                       }

    return blind_zone_data


def shapely_to_matplotlib(shapely_polygon,
                          x_data,
                          alpha=0.8,
                          fc='#FF9933',
                          ec='w',
                          linestyle='solid',
                          joinstyle='round'
                          ):

    return Polygon(polygon_within_box(x_data['center_x'], x_data['center_y'], shapely_polygon, x_data['crop_radius']),
                   closed=True,
                   fc=fc,
                   ec=ec,
                   alpha=alpha,
                   linestyle=linestyle,
                   joinstyle=joinstyle
                   )


def plot_sector(shapely_polygon=None,
                current_guideway=None,
                blocks=None,
                x_data=None,
                blind_zone=None,
                fig=None,
                ax=None,
                alpha=0.5,
                fc='#E0E0E0',
                ec='#E0E0E0'
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

    if fig is None or ax is None or x_data is None:
        return None, None

    if not isinstance(shapely_polygon, list):
        if shapely_polygon is not None:
            if isinstance(shapely_polygon, geom.multipolygon.MultiPolygon):
                polygons = list(shapely_polygon)
            else:
                polygons = [shapely_polygon]
    else:
        polygons = shapely_polygon

    if current_guideway is not None:
        ax.add_patch(get_polygon_from_guideway(current_guideway, alpha=1.0, fc='#FFFF00', ec='w'))

    if shapely_polygon is not None:
        for polygon in polygons:
            ax.add_patch(shapely_to_matplotlib(polygon, x_data, alpha=alpha, fc=fc, ec=ec))

    if blocks is not None:
        for block in blocks:
            ax.add_patch(get_polygon_from_guideway(block, alpha=1.0, fc='#FFFF00', ec='w'))
            ax.add_patch(get_polygon_from_guideway(block, alpha=1.0, fc='#000000', ec='#FFFF00', reduced=True))

    if blind_zone is not None:
        if isinstance(blind_zone, geom.multipolygon.MultiPolygon) or isinstance(blind_zone, geom.collection.GeometryCollection):
            bzs = list(blind_zone)
        else:
            bzs = [blind_zone]
        for bz in bzs:
            if isinstance(blind_zone, geom.polygon.Polygon):
                ax.add_patch(shapely_to_matplotlib(bz, x_data, alpha=1.0, fc='r', ec='r'))

    return fig, ax
