#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module supports left turns
#
#######################################################################

from lane import get_lane_index_from_left, intersects, get_turn_type, is_lane_crossing_another_street


def is_left_turn_allowed(lane_data):
    """
    Return True if a legal left turn allowed from this lane.  False otherwise.
    :param lane_data: lane dictionary
    :return: boolean
    """
    if lane_data['direction'] != 'to_intersection':
        return False
    if 'link' in lane_data['name']:
        return False
    if lane_data['lane_type'] == 'cycleway':
        return True
    if 'left' in lane_data['lane_type']:
        return True
    if lane_data['num_of_left_lanes'] == 0 \
            and lane_data['lane_type'] == ''\
            and get_lane_index_from_left(lane_data) == 0:
        return True

    return False


def get_destination_lanes_for_left_turn(origin_lane, all_lanes, nodes_dict):
    """
    Identifying destination lanes (possibly more than one).
    Assuming that the origin and destination lanes must have the same lane index from left,
    i.e. the driver is obeying the rules and turning from the most left origin lane to the most left one, and so on.
    The destination lane in some rare cases can be a turn lane for the next intersection.
    So we identify the destination lane by the index from left rather than by the lane id.
    :param origin_lane: lane dictionary of a left turn
    :param all_lanes: list of dictionaries
    :param nodes_dict: dictionary
    :return: list of valid lane destinations for the left turn
    """

    if origin_lane['name'] == 'no_name':
        return []
    if not is_left_turn_allowed(origin_lane):
        return []

    if origin_lane['lane_type'] == 'cycleway':
        return [l for l in all_lanes
                if l['name'] != origin_lane['name']
                and l['name'] != 'no_name'
                and l['direction'] == 'from_intersection'
                and intersects(origin_lane, l, all_lanes)
                and get_turn_type(origin_lane, l) == 'left_turn'
                and is_lane_crossing_another_street(origin_lane, l['name'], nodes_dict)
                and 'link' not in l['name']
                ]

    destination_index = get_lane_index_from_left(origin_lane)

    return [l for l in all_lanes
            if l['name'] != origin_lane['name']
            and l['name'] != 'no_name'
            and l['direction'] == 'from_intersection'
            and destination_index == get_lane_index_from_left(l)
            and intersects(origin_lane, l, all_lanes)
            and get_turn_type(origin_lane, l) == 'left_turn'
            and 'link' not in l['name']
            #and is_lane_crossing_another_street(origin_lane, l['name'], nodes_dict)
            ]
