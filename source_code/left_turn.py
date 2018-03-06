#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module supports left turns
#
#######################################################################

from lane import get_lane_index_from_left, intersects, get_turn_type


def is_left_turn_allowed(lane):
    """
    Return True if a legal left turn allowed from this lane.  False otherwise.
    :param lane: lane dictionary
    :return: boolean
    """
    if 'left' in lane['lane_type']:
        return True
    if lane['num_of_left_lanes'] == 0 and lane['lane_type'] == '':
        return True

    return False


def get_destination_lanes_for_left_turn(origin_lane, all_lanes):
    """
    Identifying destination lanes (possibly more than one).
    Assuming that the origin and destination lanes must have the same lane index from left,
    i.e. the driver is obeying the rules and turning from the most left origin lane to the most left one, and so on.
    The destination lane in some rare cases can be a turn lane for the next intersection.
    So we identify the destination lane by the index from left rather than by the lane id.
    :param origin_lane: lane dictionary of a left turn
    :param all_lanes: list of dictionaries
    :return: list of valid lane destinations for the left turn
    """
    if origin_lane['name'] == 'no_name':
        return []
    if not is_left_turn_allowed(origin_lane):
        return []

    destination_index = get_lane_index_from_left(origin_lane)
    return [l for l in all_lanes
            if l['name'] != origin_lane['name']
            and l['name'] != 'no_name'
            and l['direction'] == 'from_intersection'
            and destination_index == get_lane_index_from_left(l)
            and intersects(origin_lane, l, all_lanes)
            and get_turn_type(origin_lane, l) == 'left_turn'
            ]
