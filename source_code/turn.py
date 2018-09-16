#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for turns
#
#######################################################################

import copy
import math
import shapely.geometry as geom
import nvector as nv
from lane import add_space_for_crosswalk
from border import cut_border_by_polygon, get_turn_angle, to_rad, extend_vector, get_compass, \
    shift_by_bearing_and_distance, drop_small_edges, great_circle_vec_check_for_nan, is_almost_parallel
from log import get_logger


logger = get_logger()

nv_frame = nv.FrameE(a=6371e3, f=0)


def shorten_border_for_crosswalk(input_border,
                                 street_name,
                                 lanes,
                                 crosswalk_width=10,
                                 destination='from_intersection',
                                 exclude_links=True,
                                 ):
    """
    Remove the portion of the input border overlapping with any crosswalk crossing the input border.
    Scan all lanes with street names other than the street the input border belongs to,
    and identify crosswalks related to each lane.
    :param input_border: list of coordinates
    :param street_name: string
    :param lanes: list of dictionaries
    :param crosswalk_width: float
    :param destination: string
    :param exclude_links: True if exclude links, False otherwise
    :return: list of coordinates
    """
    border = copy.deepcopy(input_border)
    if destination == 'from_intersection':
        multi_string_index = -1
    else:
        multi_string_index = 0

    for l in lanes:
        if l['name'] == 'no_name' or l['name'] == street_name:
            continue
        if exclude_links and 'link' in l['name']:
            continue
        if 'median' in l:
            border_type = 'median'
        else:
            border_type = 'left_border'
        if is_almost_parallel(border, l[border_type]):
            logger.debug("Excluding %s because it is almost parallel" % l['name'])
            continue

        lb, rb = add_space_for_crosswalk(l, crosswalk_width=crosswalk_width)
        coord = lb + rb[::-1]
        polygon = geom.Polygon(coord)
        temp = cut_border_by_polygon(border, polygon, multi_string_index)
        if temp is not None:
            border = temp
            border = drop_small_edges(border)

    return border


def construct_turn_arc_with_initial_angle(origin_border,
                                          destination_border,
                                          initial_angle=15.0,
                                          number_of_points=12,
                                          turn_direction=-1.0
                                          ):
    intersection_point, vector1, vector2 = get_turn_angle(origin_border, destination_border)

    if intersection_point is None:
        return None

    from_origin_to_intersection = great_circle_vec_check_for_nan(intersection_point[1], intersection_point[0],
                                                                 vector1[1][1], vector1[1][0])
    from_destination_to_intersection = great_circle_vec_check_for_nan(intersection_point[1], intersection_point[0],
                                                                      vector2[1][1], vector2[1][0])

    bearing1 = get_compass(vector1[1], vector1[0])
    bearing2 = get_compass(vector2[0], vector2[1])
    angle = ((turn_direction*(bearing2 - bearing1) + 360) % 360)
    sin1 = math.sin(to_rad(180.0 - angle))

    l_dest = from_destination_to_intersection
    z = l_dest * sin1 / (sin1 + math.sin(to_rad(initial_angle)))
    l_origin = z * math.cos(to_rad(initial_angle)) + (l_dest - z) * math.cos(to_rad(180.0 - angle))

    if from_origin_to_intersection > l_origin:
        #  Drive along the origin vector past the intersection
        last_origin_point = extend_vector(vector1, length=l_origin, backward=False, relative=False)[1]
    else:
        # Start turning immediately
        last_origin_point = vector1[1]

    azimuth = (get_compass(intersection_point, last_origin_point) - initial_angle + 360) % 360
    point = nv_frame.GeoPoint(latitude=last_origin_point[1], longitude=last_origin_point[0], degrees=True)
    result, _azimuthb = point.geo_point(distance=100.0, azimuth=azimuth, degrees=True)
    first_orin_point = (result.longitude_deg, result.latitude_deg)
    angled_origin_border = [first_orin_point, last_origin_point]

    return construct_turn_arc(angled_origin_border,
                              destination_border,
                              number_of_points=number_of_points,
                              turn_direction=turn_direction
                              )


def construct_turn_arc(origin_border, destination_border, number_of_points=12, turn_direction=-1.0):
    """
    Construct a turn arc
    :param origin_border: list of coordinates
    :param destination_border: list of coordinates
    :param number_of_points: integer
    :param turn_direction: -1 if left turn otherwise 1
    :return: list of coordinates
    """

    intersection_point, vector1, vector2 = get_turn_angle(origin_border, destination_border)

    if intersection_point is None:
        logger.debug('Origin %r' % destination_border)
        logger.debug('Destin %r' % destination_border)
        logger.debug('Cannot find intersection point')
        return None

    from_origin_to_intersection = great_circle_vec_check_for_nan(intersection_point[1], intersection_point[0],
                                                                 vector1[1][1], vector1[1][0])
    from_destination_to_intersection = great_circle_vec_check_for_nan(intersection_point[1], intersection_point[0],
                                                                      vector2[1][1], vector2[1][0])

    bearing1 = get_compass(vector1[1], vector1[0])
    bearing2 = get_compass(vector2[0], vector2[1])
    angle = ((turn_direction*(bearing2 - bearing1) + 360) % 360)

    if from_origin_to_intersection < from_destination_to_intersection:
        distance_to_starting_point = from_origin_to_intersection
        dist_delta = 0.0
    else:
        distance_to_starting_point = from_destination_to_intersection
        dist_delta = from_origin_to_intersection - from_destination_to_intersection

    radius = distance_to_starting_point / math.tan(to_rad(angle / 2.0))
    shift = [turn_direction * 2.0 * radius * (math.sin(to_rad(angle / 2.0 * i / float(number_of_points)))) ** 2
             for i in range(0, number_of_points + 1)
             ]

    vec = [origin_border[-1], intersection_point]
    vector = [extend_vector(vec,
                            length=dist_delta + radius * (math.sin(to_rad(angle * i / float(number_of_points)))),
                            backward=False
                            )[1]
              for i in range(0, number_of_points + 1)
              ]

    return [shift_by_bearing_and_distance(vector[i], shift[i], vec, bearing_delta=turn_direction*90.0)
            for i in range(0, number_of_points + 1)
            ]


def get_turn_border(origin_lane,
                    destination_lane,
                    all_lanes,
                    border_type='left',
                    turn_direction=1,
                    use_shaped_border=False
                    ):
    """
    Create a border for a left or rigth guideway.  U-turn guideways are constructed by a separate function
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :param border_type: string either 'left' ot 'right'
    :param turn_direction: -1 if left turn, otherwise 1
    :param use_shaped_border: True if apply a shaped border for turning lane, otherwise False
    :return: list of coordinates
    """
    shaped_border = border_type + '_shaped_border'
    non_shaped_border = border_type + '_border'

    if border_type == 'median':
        non_shaped_border = 'median'
        origin_border = origin_lane['median']
    elif not use_shaped_border:
        origin_border = origin_lane[non_shaped_border]
    elif shaped_border not in origin_lane or origin_lane[shaped_border] is None:
        origin_border = origin_lane[non_shaped_border]
    else:
        origin_border = origin_lane[shaped_border]

    destination_border = destination_lane[non_shaped_border]

    if turn_direction > 0:
        crosswalk_width = origin_lane['crosswalk_width']
    else:
        crosswalk_width = 5*origin_lane['crosswalk_width']

    shorten_origin_border = shorten_border_for_crosswalk(origin_border,
                                                         origin_lane['name'],
                                                         all_lanes,
                                                         destination='to_intersection',
                                                         crosswalk_width=crosswalk_width
                                                         )
    shorten_destination_border = shorten_border_for_crosswalk(destination_border,
                                                              destination_lane['name'],
                                                              all_lanes,
                                                              destination='from_intersection',
                                                              crosswalk_width=crosswalk_width
                                                              )

    if turn_direction < 0:
        turn_arc = construct_turn_arc(shorten_origin_border,
                                      shorten_destination_border,
                                      turn_direction=turn_direction,
                                      )
    else:
        turn_arc = construct_turn_arc(shorten_origin_border,
                                      shorten_destination_border,
                                      turn_direction=turn_direction,
                                      )

    if turn_arc is None:
        logger.debug('Turn arc failed. Origin id %d, Dest id %d' % (origin_lane['id'], destination_lane['id']))
        return None

    return shorten_origin_border + turn_arc[1:-1] + shorten_destination_border
