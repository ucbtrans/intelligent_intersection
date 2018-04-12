#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module supports functions for bicycle
#
#   Reference: https://wiki.openstreetmap.org/wiki/Bicycle
#
#######################################################################


def get_bicycle_lane_location(path_data):
    """
    Find where the bicycle lane is located for a given path.
    :param path_data: dictionary
    :return: dictionary with forward and backward bicycle lane location
    """
    bicycle_forward_location = None
    bicycle_backward_location = None

    # Case L1a cycleway=lane (recommended) or cycleway:left=lane + cycleway:right=lane or  cycleway:both=lane
    if key_value_check([('cycleway', 'lane')], path_data) \
            or key_value_check([('cycleway:right', 'lane'), ('cycleway:left', 'lane')], path_data) \
            or key_value_check([('cycleway:both', 'lane')], path_data):

        bicycle_forward_location = 'right'
        bicycle_backward_location = None

    # Case L2, or M2a cycleway:right=lane
    if key_value_check([('cycleway:right', 'lane')], path_data):
        bicycle_forward_location = 'right'
        bicycle_backward_location = None

    # Case L1b cycleway:right=lane + cycleway:right:oneway=no (recommended)
    if key_value_check([('cycleway:right', 'lane'), ('cycleway:right:oneway', 'no')], path_data):
        bicycle_forward_location = 'right'
        bicycle_backward_location = 'right'

    # Case M1 cycleway=lane + oneway:bicycle=no or cycleway:left=opposite_lane + cycleway:right=lane
    if key_value_check([('cycleway', 'lane'), ('oneway:bicycle', 'no')], path_data) \
            or key_value_check([('cycleway:left', 'opposite_lane'), ('cycleway:right', 'lane')], path_data):

        bicycle_forward_location = 'right'
        bicycle_backward_location = 'left'

    # Case M2b cycleway:left=lane
    if key_value_check([('cycleway:left', 'lane'), ('cycleway:right', None)], path_data):
        bicycle_forward_location = 'left'
        bicycle_backward_location = None

    # Case M2d oneway:bicycle=no + cycleway:left=lane + cycleway:left:oneway=no
    if key_value_check([('oneway:bicycle', 'no'), ('cycleway:left', 'lane'), ('cycleway:left:oneway', 'no')], path_data):
        bicycle_forward_location = 'left'
        bicycle_backward_location = 'left'

    # Case M3a oneway:bicycle=no + cycleway:left=opposite_lane or  oneway:bicycle=no + cycleway=opposite_lane
    # Definition of M3a and M3b are ambiguous: the second option is same for both cases.
    # Considering M3b as less probable.  Removing the second "or" option form M3b
    if key_value_check([('oneway:bicycle', 'no'), ('cycleway:left', 'opposite_lane')], path_data) \
            or key_value_check([('oneway:bicycle', 'no'), ('cycleway', 'opposite_lane')], path_data):
        bicycle_forward_location = None
        bicycle_backward_location = 'left'

    # Case M3b oneway:bicycle=no + cycleway:right=opposite_lane or oneway:bicycle=no + cycleway=opposite_lane
    if key_value_check([('oneway:bicycle', 'no'), ('cycleway:right', 'opposite_lane')], path_data):
        bicycle_forward_location = None
        bicycle_backward_location = 'right'

    # More cases to be added

    return {'bicycle_forward_location': bicycle_forward_location,
            'bicycle_backward_location': bicycle_backward_location
            }


def key_value_check(list_of_key_value_pairs, path_data):
    """
    Check whether each pair of key and value in the list present in path data.
    If a value is None then the its key must be absent from the path data.
    :param list_of_key_value_pairs: list of tuples
    :param path_data: dictionary
    :return: True if all not None pairs are present, False otherwise
    """
    for key, value in list_of_key_value_pairs:
        if value is not None and key not in path_data['tags']:
            return False
        if value is None and key in path_data['tags']:
            return False
        if value is None and key not in path_data['tags']:
            continue
        if path_data['tags'][key] != value:
            return False
    return True


def is_shared(path_data):
    """
    Check if bicycle traffic is sharing the vehicle lane.
    :param path_data: dictionary
    :return: True if sharing, False otherwise
    """
    shared = False
    if 'cycleway' in path_data['tags'] and 'shared' in path_data['tags']['cycleway']:
        shared = True
    elif 'cycleway:right' in path_data['tags'] and 'shared' in path_data['tags']['cycleway:right']:
        shared = True
    elif 'cycleway' not in path_data['tags'] \
            and 'cycleway:right' not in path_data['tags'] \
            and 'cycleway:left' not in path_data['tags']:
        shared = True

    return shared
