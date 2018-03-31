#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides corrections for missing data
#
#######################################################################


from border import get_angle_between_bearings
from path import count_lanes


def manual_correction(paths):
    """
    Apply manual corrections by adding missing data
    :param paths: list of dictionaries
    :return: None
    """
    for p in paths:
        if p['id'] == 517844779:
            p['tags']['lanes'] = 4
            p['tags']['turn:lanes'] = 'left|||'

        if p['id'] == 45097701:
            p['tags']['lanes'] = 2


def extrapolate_number_of_lanes(path_data, paths):
    """
    Add missing lane data to a path based on the previous path of the same street.
    Assuming that the number of the trunk lanes are same in the path coming out of the intersection.
    :param path_data: dictionary
    :param paths: list of dictionaries
    :return: None
    """

    if 'tags' in path_data \
            and 'lanes' not in path_data['tags'] \
            and 'turn:lanes' not in path_data['tags']\
            and 'direction' in path_data['tags']\
            and path_data['tags']['direction'] == 'from_intersection'\
            and 'bearing' in path_data\
            and len(path_data['nodes']) > 0\
            and 'name' in path_data['tags']:

        prev_path = [p for p in paths
                     if 'name' in p['tags']
                     and p['tags']['name'] == path_data['tags']['name']
                     and 'direction' in p['tags']
                     and p['tags']['direction'] == 'to_intersection'
                     and 'bearing' in p
                     and abs(get_angle_between_bearings(p['bearing'], path_data['bearing'])) < 60.0
                     and len(p['nodes']) > 0
                     and p['nodes'][-1] == path_data['nodes'][0]
                    ]

        if len(prev_path) == 1:
            num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(prev_path[0])
            path_data['tags']['lanes'] = num_of_trunk_lanes


def correct_paths(paths):
    """
    Apply corrections to all paths in the list
    :param paths: list of dictionaries
    :return: None
    """
    for p in paths:
        extrapolate_number_of_lanes(p, paths)
