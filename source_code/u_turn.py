#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for u-turns
#
#######################################################################


import math
import shapely.geometry as geom
from lane import get_lane_index_from_left
from turn import shorten_border_for_crosswalk
from border import get_angle_between_bearings, shift_by_bearing_and_distance, cut_border_by_distance,\
    get_distance_between_points, get_compass, extend_vector, to_rad, extend_origin_border, extend_destination_border,\
    cut_line_by_relative_distance
from log import get_logger


logger = get_logger()


def is_u_turn_allowed(origin_lane, x_data):
    """
    Check if a U-turn is allowed for this lane
    :param origin_lane: dictionary
    :return: True if allowed, otherwise False
    """
    if origin_lane['direction'] != 'to_intersection':
        return False
    if origin_lane['lane_type'] == 'cycleway' or 'rail' in origin_lane['lane_type']:
        return False
    if get_lane_index_from_left(origin_lane):
        return False
    if 'through' in origin_lane['lane_type'] and 'left' not in origin_lane['lane_type']:
        return False
    if get_distance_between_points(origin_lane['left_border'][-1], (x_data['center_x'], x_data['center_y'])) > 25.0:
        return False
    return True


def get_destination_lanes_for_u_turn(origin_lane, all_lanes):
    """
    Identifying the destination lane for the u-turn.
    Assuming that the origin and destination lanes must have the index from left equal to zero.
    :param origin_lane: lane dictionary of a left turn
    :param all_lanes: list of dictionaries
    :return: list of valid lane destinations for the left turn
    """
    if origin_lane['name'] == 'no_name':
        return []

    return [l for l in all_lanes
            if l['name'] == origin_lane['name']
            and l['direction'] == 'from_intersection'
            and get_lane_index_from_left(l) == 0
            and abs(get_angle_between_bearings(origin_lane['bearing'], l['bearing'])) > 150.0
            and get_distance_between_points(l['left_border'][0], origin_lane['left_border'][-1]) < 25.0
            and get_distance_between_points(l['left_border'][0], l['left_border'][-1]) > 25.0
            ]


def get_u_turn_radius_and_landing_border(origin_border, destination_border):
    """
    1) Extend a perpendicular line
    2) intersect with the destination border
    3) calculate radius
    :return: 
    """

    far_away = shift_by_bearing_and_distance(origin_border[-1], 1000.0, origin_border[-2:], bearing_delta=-90.0)
    orthogonal = geom.LineString([origin_border[-1], far_away])
    destination_line = geom.LineString(destination_border)

    if orthogonal.intersects(destination_line):
        intersection_point = orthogonal.intersection(destination_line)
        pt = list(intersection_point.coords)[0]
        cut_point = destination_line.project(intersection_point)
        landing_line = cut_border_by_distance(destination_line, cut_point)[-1]
    else:
        cut_point = orthogonal.project(geom.Point(destination_border[0]))
        line0 = cut_border_by_distance(orthogonal, cut_point)[0]
        pt = list(line0.coords)[-1]
        landing_line = geom.LineString(destination_border)

    return get_distance_between_points(origin_border[-1], pt)/2.0, list(landing_line.coords)


def get_u_turn_border(origin_lane, destination_lane, all_lanes, border_type='left'):
    """
    Construct a border of a u-turn guideway
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :param border_type: string: either 'left' or 'right' or 'median'
    :return: list of coordinates
    """

    if border_type == 'median':
        destination_border = destination_lane['median']
        origin_border = origin_lane['median']
    else:
        destination_border = destination_lane[border_type + '_border']
        origin_border = origin_lane[border_type + '_border']

    cut_size = origin_lane['crosswalk_width']*5.0
    shorten_origin_border = shorten_border_for_crosswalk(origin_border,
                                                         origin_lane['name'],
                                                         all_lanes,
                                                         destination='to_intersection',
                                                         crosswalk_width=cut_size
                                                         )
    shorten_origin_border = extend_origin_border(shorten_origin_border, length=cut_size, relative=True)
    shorten_origin_border = shorten_border_for_crosswalk(shorten_origin_border,
                                                         origin_lane['name'],
                                                         all_lanes,
                                                         destination='to_intersection',
                                                         crosswalk_width=0.0
                                                         )
    shorten_destination_border = shorten_border_for_crosswalk(destination_border,
                                                              destination_lane['name'],
                                                              all_lanes,
                                                              destination='from_intersection',
                                                              crosswalk_width=cut_size
                                                              )
    shorten_destination_border = extend_destination_border(shorten_destination_border, length=cut_size, relative=True)
    shorten_destination_border = shorten_border_for_crosswalk(shorten_destination_border,
                                                              destination_lane['name'],
                                                              all_lanes,
                                                              destination='from_intersection',
                                                              crosswalk_width=0.0
                                                              )

    turn_arc = construct_u_turn_arc(shorten_origin_border, shorten_destination_border)

    if turn_arc is None:
        return None

    return shorten_origin_border + turn_arc[1:]


def construct_u_turn_arc(origin_border, destination_border, number_of_points=12):
    """
    Construct a turn arc with the destination border
    :param origin_border: list of coordinates
    :param destination_border: list of coordinates
    :param number_of_points: integer
    :return: list of coordinates
    """

    bearing1 = get_compass(origin_border[-2], origin_border[-1])
    bearing2 = get_compass(destination_border[0], destination_border[1])
    angle = abs(get_angle_between_bearings(bearing1, bearing2))

    radius, landing_border = get_u_turn_radius_and_landing_border(origin_border, destination_border)
    if radius > 50:
        logger.debug('U-turn bearings %r, %r, angle %r' % (bearing1, bearing2, angle))
        logger.warning('Radius is too large %r, landing border %r' % (radius, landing_border))
        ob = cut_line_by_relative_distance(destination_border, 0.95)
        radius, landing_border = get_u_turn_radius_and_landing_border(ob, destination_border)
        logger.debug('Retry bearings %r, %r, angle %r' % (bearing1, bearing2, angle))
        logger.debug('Adjusted radius %r, landing border %r' % (radius, landing_border))
    else:
        ob = origin_border
    shift = [2.0 * radius * (math.sin(to_rad(angle / 2.0 * i / float(number_of_points)))) ** 2
             for i in range(0, number_of_points + 1)
             ]

    vec = [ob[-1], extend_vector(ob[-2:], length=30.0, backward=False, relative=True)[-1]]
    vector = [extend_vector(vec,
                            length=radius * (math.sin(to_rad(angle * i / float(number_of_points)))),
                            backward=False
                            )[1]
              for i in range(0, number_of_points + 1)
              ]

    arc = [shift_by_bearing_and_distance(vector[i], shift[i], ob[-2:], bearing_delta=-90.0)
           for i in range(0, number_of_points + 1)
           ]

    return arc[:-1] + landing_border
