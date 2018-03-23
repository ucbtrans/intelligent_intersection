#!/usr/bin/env python
# -*- coding: utf-8 -*-

#######################################################################
#
#   This module creates guideways from list of lanes
#   Left turn algorithm:
#   1) Identify destination lanes (possibly more than one)
#   2) Extend the left border of the origin lane
#   3) Extend the left border of the destination lane
#   4) Intersect two borders and get intersection angle
#   5) Calculate turn radius from the angle between two lanes
#   6) Find the center of the circle
#   7) Build the turn left border
#   8) Build the entire left border of a guideway
#   9) Create a guideway
#
#######################################################################

import math
import shapely.geometry as geom
import osmnx as ox
from lane import extend_origin_left_border, extend_destination_left_border
from border import extend_vector, cut_border_by_distance, get_compass_bearing, get_compass, shift_vector, \
    shift_list_of_nodes, to_rad
from matplotlib.patches import Polygon
from right_turn import get_right_turn_border, get_link, get_link_destination_lane, is_right_turn_allowed, \
    get_direct_right_turn_border, get_destination_lanes_for_right_turn
from left_turn import is_left_turn_allowed, get_destination_lanes_for_left_turn
from through import is_through_allowed, get_destination_lane

def get_intersection_angle(origin_lane, destination_lane, all_lanes):
    """
    Step 4.  Intersect two borders and return intersection angle.
    Returns three objects: an intersection point, vector along the origin lane border
    and vector along the destination lane border.
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :return: tuple of three objects: (tuple of coordinates, list of coordinates, list of coordinates)
    """
    origin_line = geom.LineString(extend_origin_left_border(origin_lane, all_lanes))
    destination_line = geom.LineString(extend_destination_left_border(destination_lane))
    if not origin_line.intersects(destination_line):
        # Something went terribly wrong
        return None, None, None

    intersection_point = origin_line.intersection(destination_line)
    pt = list(intersection_point.coords)[0]
    line2 = cut_border_by_distance(destination_line, destination_line.project(intersection_point))[1]
    return pt, [pt, origin_lane['left_shaped_border'][-1]], list(line2.coords)[:2]


def get_turn_radius_and_angle(origin_lane, destination_lane, all_lanes):
    """
    Step 5.  Calculate turn radius from angle between two lanes.
    The radius is equal to the distance from the intersection to the starting point
    times tangent of the half of the angle.
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :return: a tuple of two float: radius (m) and angle (degree)
    """

    intersection_point, vector1, vector2 = get_intersection_angle(origin_lane, destination_lane, all_lanes)
    if intersection_point is None:
        return None, None, None

    distance_to_starting_point = ox.great_circle_vec(intersection_point[1], intersection_point[0],
                                                     vector1[1][1], vector1[1][0])
    distance_to_starting_point1 = geom.Point(intersection_point).distance(geom.Point(vector1[1][0], vector1[1][1]))
    bearing1 = get_compass_bearing((vector1[0][1], vector1[0][0]), (vector1[1][1], vector1[1][0]))
    bearing2 = get_compass_bearing((vector2[0][1], vector2[0][0]), (vector2[1][1], vector2[1][0]))
    angle = (bearing2 - bearing1 + 360) % 360
    return distance_to_starting_point*math.tan(angle/360.0*math.pi), \
        angle, \
        distance_to_starting_point1*math.tan(angle/360.0*math.pi)


def construct_left_border(origin_lane, destination_lane, all_lanes):
    intersection_point, vector1, vector2 = get_intersection_angle(origin_lane, destination_lane, all_lanes)
    if intersection_point is None:
        return None

    distance_to_starting_point = ox.great_circle_vec(intersection_point[1], intersection_point[0],
                                                     vector1[1][1], vector1[1][0])
    bearing1 = get_compass(vector1[1], vector1[0])
    bearing2 = get_compass(vector2[0], vector2[1])
    angle = (bearing1 - bearing2 + 360) % 360
    radius = distance_to_starting_point/math.tan(to_rad(angle/2.0))
    origin_lane['left_turn_angle'] = angle
    origin_lane['left_turn_radius'] = radius
    origin_lane['distance_to_starting_point'] = distance_to_starting_point
    n = 10
    shift = [-2.0*radius*(math.sin(to_rad(angle/2.0*i/n)))**2 for i in range(1, n+1)]
    vec = [origin_lane['left_shaped_border'][-1], intersection_point]
    vector = [extend_vector(vec, length=radius*(math.sin(to_rad(angle*i/n))), backward=False)[1]
              for i in range(1, n)
              ]
    left_border = shift_list_of_nodes(vector, shift, direction_reference=vec)

    return left_border


def define_center(origin_lane, destination_lane, all_lanes):
    """
    Step 6.  Get the center of the turn
    :param origin_lane:
    :param destination_lane:
    :param all_lanes:
    :return: tuple of coordinates
    """

    radius, angle, radius1 = get_turn_radius_and_angle(origin_lane, destination_lane, all_lanes)

    origin_lane['left_turn_radius'] = radius
    origin_lane['left_turn_radius1'] = radius1
    origin_lane['left_turn_angle'] = angle
    origin_lane['left_turn_center'] = shift_vector(origin_lane['left_shaped_border'][-2:], -radius)[-1]
    return origin_lane['left_turn_center']


def get_guideway_left_border(origin_lane, destination_lane, all_lanes):
    """
    Step 8.  Build the left border for the entire guideway
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionary
    :return: list of coordinates
    """
    turn_left_border = construct_left_border(origin_lane, destination_lane, all_lanes)
    if turn_left_border is None:
        return None
    destination_border = geom.LineString(destination_lane['left_border'])
    landing_point = destination_border.project(geom.Point(turn_left_border[-1]))
    landing_border = cut_border_by_distance(destination_border, landing_point)[1]
    return turn_left_border[:-1] + list(landing_border.coords)


def create_left_turn_guideway(origin_lane, destination_lane, all_lanes):
    """
    Step 9. Calculate the right border and create a guideway
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionary
    :return: dictionary
    """

    guideway = {
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
    }

    left_border = get_guideway_left_border(origin_lane, destination_lane, all_lanes)
    if left_border is None:
        return None

    right_border = shift_list_of_nodes(left_border, [origin_lane['width'][-1]]*len(left_border))

    guideway['left_border'] = origin_lane['left_shaped_border'] + left_border
    guideway['right_border'] = origin_lane['right_shaped_border'] + right_border

    return guideway


def get_left_turn_guideways(all_lanes, nodes_dict, angle_delta=2.5):
    """
    Compile a list of guideways for all legal left turns
    :param all_lanes: list of dictionaries
    :param angle_delta: float in degrees
    :param nodes_dict: dictionary
    :return: list of dictionaries
    """

    guideways = []
    for origin_lane in all_lanes:
        if 'L' in origin_lane['lane_id'] or is_left_turn_allowed(origin_lane):
            for destination_lane in get_destination_lanes_for_left_turn(origin_lane, all_lanes, nodes_dict):
                guideway_data = get_direct_right_turn_guideway(origin_lane,
                                                               destination_lane,
                                                               all_lanes,
                                                               turn_type='left',
                                                               angle_delta=angle_delta
                                                              )
                # guideway = create_left_turn_guideway(origin_lane, destination_lane, all_lanes)
                if guideway_data is not None:
                    guideways.append(guideway_data)
    return guideways


def create_right_turn_guideway(origin_lane, all_lanes):
    """
    Calculate the right border and create a guideway
    :param origin_lane: dictionary
    :param all_lanes: list of dictionary
    :return: dictionary
    """

    guideway = {
        'type': 'right',
        'origin_lane': origin_lane,
    }

    link_lane = get_link(origin_lane, all_lanes)
    if link_lane is None:
        destination_lanes = get_destination_lanes_for_right_turn(origin_lane, all_lanes)
        if len(destination_lanes) > 0:
            return get_direct_right_turn_guideway(origin_lane,
                                                  destination_lanes[0],
                                                  all_lanes,
                                                  turn_type='right',
                                                  angle_delta=0.0
                                                  )
        else:
            return None

    destination_lane = get_link_destination_lane(link_lane, all_lanes)
    if destination_lane is None:
        return None

    if origin_lane['left_shaped_border'] is None:
        left_border_type = 'left_border'
    else:
        left_border_type = 'left_shaped_border'
    if origin_lane['right_shaped_border'] is None:
        right_border_type = 'right_border'
    else:
        right_border_type = 'right_shaped_border'

    guideway['destination_lane'] = destination_lane
    guideway['left_border'] = get_right_turn_border(origin_lane[left_border_type],
                                                    link_lane['left_border'],
                                                    destination_lane['left_border']
                                                    )
    guideway['right_border'] = get_right_turn_border(origin_lane[right_border_type],
                                                     link_lane['right_border'],
                                                     destination_lane['right_border']
                                                     )
    if guideway['left_border'] is None or guideway['right_border'] is None:
        return None

    return guideway


def get_through_guideway(origin_lane, destination_lane):
    return {
        'type': 'through',
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
        'left_border': origin_lane['left_border'][:-1] + destination_lane['left_border'],
        'right_border': origin_lane['right_border'][:-1] + destination_lane['right_border']
    }


def get_through_guideways(all_lanes):
    guideways = []
    for origin_lane in all_lanes:
        if is_through_allowed(origin_lane):
            destination_lane = get_destination_lane(origin_lane, all_lanes)
            if destination_lane is not None:
                guideways.append(get_through_guideway(origin_lane, destination_lane))
    return guideways


def get_direct_right_turn_guideway(origin_lane, destination_lane, all_lanes, turn_type='right', angle_delta=2.5):
    """
    Create a right turn guideway if there is no link lane connecting origin and destination
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :param turn_type: string: 'right' for a right turn, left' a for left one
    :param angle_delta: float in degrees
    :return: dictionary
    """

    if turn_type == 'right':
        if not is_right_turn_allowed(origin_lane, all_lanes):
            return None
        angle_delta = 0.0
        turn_direction = 1
    else:
        if not is_left_turn_allowed(origin_lane):
            return None
        angle_delta = angle_delta
        turn_direction = -1

    guideway = {
        'type': turn_type,
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
    }
    left_border = get_direct_right_turn_border(origin_lane,
                                               destination_lane,
                                               all_lanes,
                                               border_type='left',
                                               angle_delta=angle_delta,
                                               turn_direction=turn_direction
                                               )
    if left_border is None:
        return None

    right_border = get_direct_right_turn_border(origin_lane,
                                                destination_lane,
                                                all_lanes,
                                                border_type='right',
                                                angle_delta=angle_delta,
                                                turn_direction=turn_direction
                                                )
    if right_border is None:
        return None

    guideway['left_border'] = left_border
    guideway['right_border'] = right_border
    return guideway


def get_direct_right_turn_guideways(all_lanes):
    """
    Create a list of right turn guideways for lanes not having an additional link to the destination
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """
    guideways = []
    for origin_lane in [l for l in all_lanes if is_right_turn_allowed(l, all_lanes)]:
        for destination_lane in get_destination_lanes_for_right_turn(origin_lane, all_lanes):
            guideway = get_direct_right_turn_guideway(origin_lane, destination_lane, all_lanes)
            if guideway is not None:
                guideways.append(guideway)

    return guideways


def get_right_turn_guideways(all_lanes):
    """
    Create a list of right turn guideways for lanes having an additional link to the destination
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """
    guideways = [create_right_turn_guideway(l, all_lanes) for l in all_lanes if is_right_turn_allowed(l, all_lanes)]
    return [g for g in guideways if g is not None]


def get_polygon_from_guideway(guideway, fc='y', ec='w', alpha=0.8, linestyle='dashed', joinstyle='round'):
    """
    Get a polygon from a lane
    """

    polygon_sequence = guideway['left_border'] + guideway['right_border'][::-1]

    return Polygon(polygon_sequence,
                   closed=True,
                   fc=fc,
                   ec=ec,
                   alpha=alpha,
                   linestyle=linestyle,
                   joinstyle=joinstyle
                   )


def plot_guideways(guideways, fig=None, ax=None, cropped_intersection=None,
                   fig_height=15,
                   fig_width=15,
                   axis_off=False,
                   edge_linewidth=1,
                   margin=0.02,
                   bgcolor='#CCFFE5',
                   edge_color='#FF9933',
                   alpha=1.0,
                   fc='y',
                   ec='w'
                        ):
    """
    Plot lanes for existing street plot
    :param guideways:
    :param fig:
    :param ax:
    :param cropped_intersection:
    :param fig_height:
    :param fig_width:
    :param axis_off:
    :param edge_linewidth:
    :param margin:
    :param bgcolor:
    :param edge_color:
    :return:
    """

    if fig is None or ax is None:
        if cropped_intersection is None:
            return None, None
        return None, None

    for guideway in guideways:
        ax.add_patch(get_polygon_from_guideway(guideway, alpha=alpha, fc=fc, ec=ec))

    return fig, ax
