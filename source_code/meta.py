#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module creates meta data
#
#######################################################################


import datetime
from right_turn import get_connected_links
from bicycle import key_value_check, get_bicycle_lane_location, is_shared
from lane import set_ids, get_link_from_and_to
from public_transit import get_public_transit_stop


def set_meta_data(lanes, stops, max_distance=20.0):
    """
    Set meta data for all lanes related to the intersection
    :param lanes: 
    :return: 
    """

    set_ids(lanes)
    for lane_data in lanes:
        lane_data['meta_data'] = get_lane_meta_data(lane_data, lanes, stops, max_distance=max_distance)


def get_lane_meta_data(lane_data, all_lanes, stops, max_distance=20.0):
    """
    Create meta data dictionary for a lane (i.e. approach or exit)
    :param lane_data: dictionary of all lanes related to the intersection
    :param all_lanes: list of all lanes related to the intersection
    :return: dictionary
    """
    meta_data = {}

    if 'num_of_trunk_lanes' in lane_data:
        meta_data['total_number_of_vehicle_lanes'] = lane_data['num_of_left_lanes'] \
                                                     + lane_data['num_of_right_lanes'] \
                                                     + lane_data['num_of_trunk_lanes']
        meta_data['number_of_left-turning_lanes'] = lane_data['num_of_left_lanes']
        meta_data['number_of_right-turning_lanes'] = lane_data['num_of_right_lanes']

    if 'name' in lane_data:

        if 'no_name' in lane_data['name']:
            from_name, to_name = get_link_from_and_to(lane_data, all_lanes)
            if from_name is None or to_name is None:
                meta_data['identification'] = lane_data['name'] + ' ' + lane_data['direction']
            else:
                meta_data['identification'] = from_name + ' - ' + to_name + ' Link ' + lane_data['direction']
        else:
            meta_data['identification'] = lane_data['name'] + ' ' + lane_data['direction']
    else:
        meta_data['identification'] = 'undefined_name' + ' ' + lane_data['direction']

    if 'id' in lane_data:
        meta_data['id'] = lane_data['id']
    else:
        meta_data['id'] = None

    if len(get_connected_links(lane_data, all_lanes)) > 0:
        meta_data['right_turn_dedicated_link '] = 'yes'
    else:
        meta_data['right_turn_dedicated_link'] = 'no'

    meta_data['bicycle_lane_on_the_right'] = None
    meta_data['bicycle_lane_on_the_left'] = None

    if 'path' not in lane_data:
        meta_data['bicycle_lane_on_the_right'] = 'no'
        meta_data['bicycle_lane_on_the_left'] = 'no'
    else:
        for p in lane_data['path']:
            if key_value_check([('bicycle', 'no')], p) or is_shared(p):
                meta_data['bicycle_lane_on_the_right'] = 'no'
                meta_data['bicycle_lane_on_the_left'] = 'no'
                break

            right, left = where_is_bicycle_lane(p)
            if meta_data['bicycle_lane_on_the_right'] is None:
                meta_data['bicycle_lane_on_the_right'] = right
            if meta_data['bicycle_lane_on_the_left'] is None:
                meta_data['bicycle_lane_on_the_left'] = left

    if 'rail' in lane_data['lane_type']:
        meta_data['rail_track'] = 'yes'
    else:
        meta_data['rail_track'] = 'no'
        node_set = set(lane_data['nodes'])
        for l in all_lanes:
            if 'rail' not in l['lane_type']:
                continue
            if len(node_set & set(l['nodes'])) > 0:
                meta_data['rail_track'] = 'yes'
                break

    if 'lane_type' in lane_data:
        meta_data['lane_type'] = lane_data['lane_type']

    meta_data['traffic_signals'] = None
    meta_data['number_of_crosswalks'] = None
    if 'footway' in lane_data and lane_data['footway'] == 'crossing':
        meta_data['number_of_crosswalks'] = 1
    if 'crossing' in lane_data:
        meta_data['number_of_crosswalks'] = 1
        if 'traffic_signal' in lane_data['crossing']:
            meta_data['traffic_signals'] = 'yes'
        else:
            meta_data['traffic_signals'] = 'no'

    meta_data['compass'] = lane_data['compass']

    if get_public_transit_stop(lane_data, stops, max_distance=max_distance):
        meta_data['public_transit_stop'] = 'yes'
    else:
        meta_data['public_transit_stop'] = None

    meta_data['timestamp'] = str(datetime.datetime.now())

    return meta_data


def where_is_bicycle_lane(p):
    """
    Define bicycle lane location for meta_data
    :param p: dictionary
    :return: tuple of two strings.  Each element is either yes or no
    """
    location = get_bicycle_lane_location(p)
    right = 'no'
    left = 'no'
    if location['bicycle_forward_location'] is None and location['bicycle_backward_location'] is None:
        return None, None
    if location['bicycle_forward_location'] == 'right' or location['bicycle_backward_location'] == 'right':
        right = 'yes'
    if location['bicycle_forward_location'] == 'left' or location['bicycle_backward_location'] == 'left':
        left = 'yes'

    return right, left
