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
    get_distance_between_points, get_compass, extend_vector, to_rad, shift_list_of_nodes


def is_u_turn_allowed(origin_lane):
    if origin_lane['direction'] != 'to_intersection':
        return False
    if origin_lane['lane_type'] == 'cycleway' or 'rail' in origin_lane['lane_type']:
        return False
    if get_lane_index_from_left(origin_lane):
        return False
    if 'through' in origin_lane['lane_type'] and 'left' not in origin_lane['lane_type']:
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
    if not is_u_turn_allowed(origin_lane):
        return []

    return [l for l in all_lanes
            if l['name'] == origin_lane['name']
            and l['direction'] == 'from_intersection'
            and get_lane_index_from_left(l) == 0
            and abs(get_angle_between_bearings(origin_lane['bearing'], l['bearing'])) > 150.0
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
        landing_line = destination_border

    return get_distance_between_points(origin_border[-1], pt)/2.0, list(landing_line.coords)


def get_u_turn_border(origin_lane, destination_lane, all_lanes, border_type='left'):
    """
    Construct a border of a u-turn guideway
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :param border_type: string: either 'left' or 'right'
    :return: list of coordinates
    """

    destination_border = destination_lane[border_type + '_border']
    origin_border = origin_lane[border_type + '_border']

    shorten_origin_border = shorten_border_for_crosswalk(origin_border,
                                                         origin_lane['name'],
                                                         all_lanes,
                                                         destination='to_intersection',
                                                         )

    turn_arc = construct_u_turn_arc(shorten_origin_border, destination_border)

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
    angle = (((bearing2 - bearing1) + 360) % 360)
    angle = min(abs(angle), 180.0)

    radius, landing_border = get_u_turn_radius_and_landing_border(origin_border, destination_border)
    shift = [2.0 * radius * (math.sin(to_rad(angle / 2.0 * i / float(number_of_points)))) ** 2
             for i in range(0, number_of_points + 1)
             ]

    vec = [origin_border[-1], extend_vector(origin_border[-2:], length=30.0, backward=False, relative=True)[-1]]
    vector = [extend_vector(vec,
                            length=radius * (math.sin(to_rad(angle * i / float(number_of_points)))),
                            backward=False
                            )[1]
              for i in range(0, number_of_points + 1)
              ]

    temp = shift_list_of_nodes(vector, shift, direction_reference=origin_border[-2:])

    for i in range(0, number_of_points + 1):
        res = shift_by_bearing_and_distance(vector[i], shift[i], origin_border[-2:], bearing_delta=-90.0)
        temp[i] = res

    return temp[:-1] + landing_border  # shift_list_of_nodes(vector, shift, direction_reference=vec)
