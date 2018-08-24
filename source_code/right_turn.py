#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module constructs right turn
#
#######################################################################


import shapely.geometry as geom
from border import cut_border_by_distance, extend_vector, extend_both_sides_of_a_border
from lane import get_lane_index_from_right, get_turn_type, intersects
from log import get_logger


logger = get_logger()


def is_right_turn_allowed(lane_data, all_lanes):
    """
    Define if it it is OK to turn right from this lane
    :param lane_data: dictionary
    :param all_lanes: list of dictionaries
    :return: True if right turn permitted, False otherwise
    """

    if 'right' in lane_data['lane_type'] or 'R ' in lane_data['lane_id']:
        return True

    if lane_data['lane_id'] == '1' \
            and lane_data['lane_type'] == '' \
            and lane_data['direction'] == 'to_intersection' \
            and get_lane_index_from_right(lane_data) == 0:
        return True

    if lane_data['lane_type'] == 'cycleway' and lane_data['direction'] == 'to_intersection':
        return True

    if lane_data['lane_type'] == 'through' \
            and lane_data['direction'] == 'to_intersection' \
            and get_lane_index_from_right(lane_data) == 0 \
            and len(get_connected_links(lane_data, all_lanes)) > 0:
        return True

    return False


def get_connected_links(origin_lane, all_lanes):
    """
    Get a list of trunk link lanes starting from the given origin lane.
    :param origin_lane: dictionary
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """
    if 'walk' in origin_lane['lane_type'] or 'rail' in origin_lane['lane_type']:
        return []

    return [l for l in all_lanes
            if 'walk' not in l['lane_type']
            and 'rail' not in l['lane_type']
            and 'highway' in l['path'][0]['tags']
            and 'link' in l['path'][0]['tags']['highway']
            and l['nodes'][0] in origin_lane['nodes']
            ]


def get_link(origin_lane, all_lanes):
    """
    Check if a link for a turn exists for a lane and return it, or None if no link found
    :param origin_lane: dictionary
    :param all_lanes: list of dictionaries
    :return: dictionary or None
    """

    links = get_connected_links(origin_lane, all_lanes)
    if len(links) > 0:
        return links[0]
    else:
        return None


def get_link_destination_lane(link_lane, all_lanes):
    """
    Get destination lane for a link
    :param link_lane: dictionary
    :param all_lanes: list of dictionaries
    :return: dictionary
    """
    res = [l for l in all_lanes
           if link_lane['nodes'][-1] in l['nodes']
           and link_lane['lane_id'] == l['lane_id']
           and l['direction'] == 'from_intersection'
           and 'link' not in l['path'][0]['tags']['highway']
           ]

    if len(res) > 0:
        return res[0]
    else:
        return None


def get_right_turn_border(origin_border, link_border, destination_border):
    """
    Construct either left or right border for a right turn via link
    :param origin_border: list of coordinates
    :param link_border: list of coordinates
    :param destination_border: list of coordinates
    :return: list of coordinates
    """

    last_segment = [origin_border[-2], origin_border[-1]]
    extended = extend_vector(last_segment, length=1000.0, backward=False)
    origin_line = geom.LineString(origin_border[:-1] + extended[1:])
    extended_link = extend_both_sides_of_a_border(link_border)
    link_line = geom.LineString(extended_link)
    if not origin_line.intersects(link_line):
        logger.error('Link border does not intersect the origin border')
        return None

    intersection_point1 = origin_line.intersection(link_line)
    origin_line1 = cut_border_by_distance(origin_line, origin_line.project(intersection_point1))[0]
    ct1 = cut_border_by_distance(link_line, link_line.project(intersection_point1))
    if len(ct1) < 2:
        logger.error('Link is too short')
        return None

    link_line1 = ct1[1]

    destination_line = geom.LineString(destination_border)
    if not destination_line.intersects(link_line1):
        logger.error('Link border does not intersect the destination border')
        return None

    intersection_point2 = destination_line.intersection(link_line1)
    line2 = cut_border_by_distance(destination_line, destination_line.project(intersection_point2))[1]

    return list(origin_line1.coords) + link_border[1:-1] + list(line2.coords)


def get_destination_lanes_for_right_turn(origin_lane, all_lanes):
    """
    Identifying destination lanes (possibly more than one).
    Assuming that the origin and destination lanes must have the same lane index from right,
    i.e. the driver is obeying the rules and turning from the most right origin lane to the most right one, and so on.
    The destination lane in some rare cases can be a turn lane for the next intersection.
    So we identify the destination lane by the index from right rather than by the lane id.
    :param origin_lane: lane dictionary of a left turn
    :param all_lanes: list of dictionaries
    :return: list of valid lane destinations for the left turn
    """

    if origin_lane['name'] == 'no_name':
        return []
    if not is_right_turn_allowed(origin_lane, all_lanes):
        return []

    destination_index = get_lane_index_from_right(origin_lane)
    return [l for l in all_lanes
            if l['name'] != origin_lane['name']
            and l['name'] != 'no_name'
            and l['direction'] == 'from_intersection'
            and destination_index == get_lane_index_from_right(l)
            and intersects(origin_lane, l, all_lanes)
            and get_turn_type(origin_lane, l) == 'right_turn'
            ]
