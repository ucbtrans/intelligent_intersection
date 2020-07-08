#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module supports trough guideways
#
#######################################################################


from border import get_angle_between_bearings, get_distance_between_points
from lane import get_lane_index_from_right
from turn import is_turn_allowed

def is_through_allowed(lane_data):
    """
    Check if a through driving is allowed for this lane
    :param lane_data: dictionary
    :return: True if allowed, False otherwise
    """
    if not is_turn_allowed(lane_data):
        return False
    if lane_data['direction'] != 'to_intersection':
        return False
    if 'through' in lane_data['lane_type'] or lane_data['lane_type'] == '' or 'rail' in lane_data['lane_type']:
        return True
    if lane_data['lane_type'] == 'cycleway':
        return True

    return False


def get_destination_lane(lane_data, all_lanes, min_len=21.0):
    """
    Get destination lane for through driving
    :param lane_data: dictionary
    :param all_lanes: list of dictionaries
    :return: dictionary
    """

    # Try common node first
    res = [l for l in all_lanes
           if lane_data['nodes'][-1] == l['nodes'][0]
           and lane_data['lane_id'] == l['lane_id']
           and l['direction'] == 'from_intersection'
           and - 30.0 < get_angle_between_bearings(lane_data['bearing'], l['bearing']) < 30.0
           and ("length" not in l or l["length"] > min_len)
           ]
    if len(res) > 0:
        return res[0]

    # Try same street name
    res = [l for l in all_lanes
           if lane_data['name'] == l['name']
           and lane_data['lane_id'] == l['lane_id']
           and l['direction'] == 'from_intersection'
           and - 60.0 < get_angle_between_bearings(lane_data['bearing'], l['bearing']) < 60.0
           and get_distance_between_points(lane_data['median'][-1], l['median'][0]) < 15.0
           and ("length" not in l or l["length"] > min_len)
           ]
    if len(res) > 0:
        return res[0]

    # Try all other possible options
    res = [l for l in all_lanes
           if -30.0 < get_angle_between_bearings(lane_data['bearing'], l['bearing']) < 30.0
           and int(lane_data['lane_id'][0]) - 1 == get_lane_index_from_right(l)
           and l['direction'] == 'from_intersection'
           and get_distance_between_points(lane_data['median'][-1], l['median'][0]) < 10.0
           and ("length" not in l or l["length"] > min_len)
           ]
    if len(res) > 0:
        return res[0]

    return None
