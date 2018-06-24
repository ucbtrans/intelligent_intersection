#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module calculates blind zones
#
#######################################################################


import shapely.geometry as geom
from matplotlib.patches import Polygon
from matplotlib.patches import Circle
from guideway import get_polygon_from_guideway
from border import get_compass, get_distance_between_points, get_closest_point, cut_border_by_polygon, get_box
from conflict import get_polygon_from_conflict_zone, cut_guideway_borders_by_conflict_zone
import nvector as nv
from log import get_logger


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


def get_point_by_azimuth(point, azimuth, distance=10000.0):
    pt = nv_frame.GeoPoint(latitude=point[1], longitude=point[0], degrees=True)
    result, _azimuthb = pt.geo_point(distance=distance, azimuth=azimuth, degrees=True)
    return result.longitude_deg, result.latitude_deg


def is_azimuth_in_the_shadow(point, border, azimuth=0.0):
    return geom.LineString(border).intersects(geom.LineString([point, get_point_by_azimuth(point, azimuth)]))


def get_sector_polygon(point, block):
    min_azimuth, max_azimuth, min_point, max_point = get_sector(point, block)

    bissectrice = (min_azimuth + max_azimuth)/2.0
    inverted_bissectrice = (bissectrice + 180.0) % 360.0

    if not is_azimuth_in_the_shadow(point, block['reduced_left_border'], azimuth=bissectrice):
        if is_azimuth_in_the_shadow(point, block['reduced_left_border'], azimuth=inverted_bissectrice):
            # Invert the bissectrice direction
            logger.debug("Inverting bissectrice direction. Block: %d, %r %r"
                         % (block['id'], bissectrice, inverted_bissectrice)
                         )
            bissectrice = inverted_bissectrice
        else:
            logger.warning("Bissectrice does not intersect the blocking element. Block Id: %d" % block['id'])
            return None

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
    for pt1 in (block['reduced_left_border'] + block['reduced_right_border'][::-1])[1:]:
        temp_block = {'reduced_left_border': [pt0, pt1],
                      'median': block['median'],
                      'reduced_right_border': [],
                      'id': block['id']
                      }
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


def get_shapely_polygon_from_guideway(guideway_data, prefix=''):
    """
    Get a shapely pogon from a guidewya using either the entire left and right border 
    or reduced borders (up to the last conflict zone)
    :param guideway_data: guideway dictionary
    :param prefix: string: either empty or 'reduced'
    :return: shapely polygon
    """
    if prefix + 'left_border' in guideway_data and prefix + 'right_border' in guideway_data:
        polygon = geom.Polygon(guideway_data[prefix + 'left_border'] + guideway_data[prefix + 'right_border'][::-1])
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        return polygon
    else:
        return None


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

    block_polygon = get_shapely_polygon_from_guideway(block)
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


def get_shadow_polygon_list(point, block):
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
        return []

    if sector_polygon.intersects(block_polygon):
        try:
            polygons = list(sector_polygon.difference(block_polygon))
        except Exception as e:
            logger.exception("Block Id: %d. Can not intersect with the sector" % block['id'])
            logger.exception(e)
            return sector_polygon

        for i, x in enumerate(polygons):
            if(isinstance(x, geom.polygon.Polygon) or isinstance(x, geom.multipolygon.MultiPolygon)) and not x.is_valid:
                polygons[i] = x.buffer(0)
        pt = geom.Point(point)
        polygons.sort(key=lambda xx: pt.distance(xx))
        logger.debug("Difference between sector and block %d identified, distances: %s"
                     % (block['id'], ",".join([str(pt.distance(x)) for x in polygons])))
        return polygons[1:]
    else:
        logger.error("Block Id: %d. Something went terribly wrong" % block['id'])
        return []


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


def get_shadow_from_list(point, blocking_guideway, shadowed_guideway):
    polygon = geom.Polygon(shadowed_guideway['left_border'] + shadowed_guideway['right_border'][::-1])
    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    result = None

    for shadow_polygon in get_shadow_polygon_list(point, blocking_guideway):
        if shadow_polygon is not None and polygon.intersects(shadow_polygon):
            x = polygon.intersection(shadow_polygon)
            if isinstance(x, geom.polygon.Polygon) or isinstance(x, geom.multipolygon.MultiPolygon):
                if not x.is_valid:
                    x = x.buffer(0)
                logger.debug("Adding a blind element. Area: %r" % x.area)
                if result is None:
                    result = x
                else:
                    result = result.union(x)
            else:
                logger.warning("Unexpected difference type: %s, block: %d, shadowed guideway %d"
                               % (type(x), blocking_guideway['id'], shadowed_guideway['id'])
                               )

    return result


def get_shadows(point, all_guidways, shadowed_guideway, blocking_ids=[]):
    result = None
    for g in all_guidways:
        if g['type'] == 'bicycle' or g['type'] == 'footway' or g['id'] == shadowed_guideway['id']:
            continue
        p = get_shadow_from_list(point, g, shadowed_guideway)

        if p is not None:
            logger.debug("Adding a blind zone blocked by guideway id: %d. Area: %r" % (g['id'], p.area))
            blocking_ids.append(g['id'])
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
        shortened_median = cut_border_by_polygon(guideway_data['median'],
                                                 conflict_zone['polygon'],
                                                 multi_string_index=0
                                                 )
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


def cut_blind_zone_by_conflict_zone(blind_zone_polygon, conflict_zone, guideway_data):
    """
    Cut blind zone by the conflict zone, 
    i.e. leaving the portion of the blind zone that is located before the conflict zone along the traffic
    :param blind_zone_polygon: blind zone dictionary
    :param conflict_zone: conflict zone dictionary
    :param guideway_data: guideway dictionary
    :return: 
    """
    if blind_zone_polygon is None:
        return None
    if not blind_zone_polygon.is_valid:
        blind_zone_polygon = blind_zone_polygon.buffer(0)

    left_border, median, right_border = cut_guideway_borders_by_conflict_zone(guideway_data, conflict_zone)
    reduced_polygon = geom.Polygon(left_border + right_border[::-1])
    if not reduced_polygon.is_valid:
        reduced_polygon = reduced_polygon.buffer(0)

    if reduced_polygon.intersects(blind_zone_polygon):
        reduced_blind_zone = blind_zone_polygon.intersection(reduced_polygon)
        if not reduced_blind_zone.is_valid:
            reduced_blind_zone = reduced_blind_zone.buffer(0)
        return reduced_blind_zone
    else:
        return blind_zone_polygon


def get_blind_zone_data(point, current_guideway, conflict_zone, blocking_guideways, all_guideways):
    """
    Get blind zone data
    :param point_of_view: normalized coordinates along the current guideway: (x,y), where x and y within [0.0,1.0]
    :param current_guideway: guideway dictionary
    :param conflict_zone: conflict zone dictionary.  It must belong to the current guideway
    :param blocking_guideways: list of guideway dictionaries representing guideways creating blind zones
    :param all_guideways: list of all guideway dictionaries in the intersection
    :return: blind zone dictionary
    """

    logger.debug("============================")
    logger.debug("Starting search for blind zones. Current guideway: %d, Point %r" % (current_guideway['id'], point))
    if conflict_zone['guideway1_id'] != current_guideway['id']:
        return None

    candidates_for_conflict_guideway = [g for g in all_guideways if g['id'] == conflict_zone['guideway2_id']]
    if candidates_for_conflict_guideway:
        conflict_guideway = candidates_for_conflict_guideway[0]
    else:
        return None

    point_of_view = normalized_to_geo(point, current_guideway, conflict_zone)
    blocking_ids = []
    blind_zone_polygon = get_shadows(point_of_view, blocking_guideways, conflict_guideway, blocking_ids)

    if blind_zone_polygon is not None:
        logger.info("Blind zone found for the current guideway: %d. Area: %r"
                    % (current_guideway['id'], blind_zone_polygon.area))
    else:
        logger.debug("Blind zone not found. Current guideway: %d." % current_guideway['id'])

    blind_zone_data = {'point': point,
                       'geo_point': point_of_view,
                       'guideway_id': current_guideway['id'],
                       'conflict_zone': conflict_zone,
                       'blocking_ids': blocking_ids,
                       'polygon': cut_blind_zone_by_conflict_zone(blind_zone_polygon, conflict_zone, conflict_guideway)
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
    north, south, east, west = get_box(x_data['center_x'], x_data['center_y'], size=x_data['crop_radius'])
    boundary_polygon = geom.Polygon([(west, north), (east, north), (east, south), (west, south)])
    polygon_within_boundaries = shapely_polygon.intersection(boundary_polygon)

    if isinstance(polygon_within_boundaries, geom.multipolygon.MultiPolygon):
        pols = []
        for p in list(polygon_within_boundaries):
            pol = Polygon(list(geom.mapping(p)['coordinates'][0]),
                          closed=True,
                          fc=fc,
                          ec=ec,
                          alpha=alpha,
                          linestyle=linestyle,
                          joinstyle=joinstyle
                          )
            pols.append(pol)
        return pols

    else:
        return [Polygon(list(geom.mapping(polygon_within_boundaries)['coordinates'][0]),
                        closed=True,
                        fc=fc,
                        ec=ec,
                        alpha=alpha,
                        linestyle=linestyle,
                        joinstyle=joinstyle
                        )
                ]


def plot_sector(shapely_polygon=None,
                current_guideway=None,
                blocks=None,
                x_data=None,
                blind_zone=None,
                point_of_view=None,
                conflict_zone=None,
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
        ax.add_patch(get_polygon_from_guideway(current_guideway,
                                               alpha=1.0,
                                               fc='#CCFF99',
                                               ec='#000000',
                                               linestyle='solid'
                                               )
                     )

    if shapely_polygon is not None:
        for polygon in polygons:
            for pol in shapely_to_matplotlib(polygon, x_data, alpha=alpha, fc=fc, ec=ec):
                ax.add_patch(pol)

    if blocks is not None:
        for block in blocks:
            ax.add_patch(get_polygon_from_guideway(block, alpha=1.0, fc='#FFFF00', ec='w'))
            ax.add_patch(get_polygon_from_guideway(block, alpha=1.0, fc='#000000', ec='#FFFF00', reduced=True))

    if conflict_zone is not None:
        if isinstance(conflict_zone['polygon'], geom.multipolygon.MultiPolygon):
            polygons = list(conflict_zone['polygon'])
        else:
            polygons = [conflict_zone['polygon']]

        for polygon in polygons:
            ax.add_patch(get_polygon_from_conflict_zone(polygon, alpha=1.0, fc='#660066', ec='w'))

    if blind_zone is not None:
        if isinstance(blind_zone, geom.multipolygon.MultiPolygon) or isinstance(blind_zone,
                                                                                geom.collection.GeometryCollection
                                                                                ):
            bzs = list(blind_zone)
        else:
            bzs = [blind_zone]
        logger.debug("Blind zone consists of %d polygons" % len(bzs))
        for bz in bzs:
            if isinstance(bz, geom.polygon.Polygon):
                logger.debug("Area %r" % bz.area)
                for pol in shapely_to_matplotlib(bz, x_data, alpha=1.0, fc='r', ec='w'):
                    ax.add_patch(pol)

    if point_of_view is not None:
        marker = Circle(point_of_view, radius=.000015, fc='#005500', ec='w')
        ax.add_patch(marker)

    return fig, ax
