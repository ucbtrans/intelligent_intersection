#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module creates lanes for the intersection
#
#######################################################################

from border import shift_list_of_nodes
import copy

def get_num_of_lanes(path):
    """
    Get the number of lanes from path
    :param path: dictionary
    :return: integer
    """
    # u'turn:lanes:forward': u'left;through|right'
    # u'lanes': u'3',
    # u'lanes:backward': u'1',
    # u'lanes:forward': u'2',
    # "u'lanes:forward'"

    if 'lanes' in path['tags']:
        return int(path['tags']['lanes'])

    return 1


def count_lanes(path):
    """
    Calculate the number of left, right and trunk lanes
    :param path: dictionary
    :return: tuple of three integers: num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes
    """

    num_of_lanes = get_num_of_lanes(path)

    if 'turn:lanes' in path['tags']:
        lane_types = path['tags']['turn:lanes'].split('|')
    else:
        lane_types = [''] * num_of_lanes

    lane_types = lane_types[::-1]
    num_of_left_lanes = lane_types.count('left')
    num_of_right_lanes = lane_types.count('right')
    num_of_trunk_lanes = num_of_lanes - num_of_left_lanes - num_of_right_lanes

    return num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes


def add_borders_to_path(path, nodes_dict, width=3.048):
    path = remove_nodes_without_coordinates(path, nodes_dict)
    if len(path['nodes']) < 2:
        path['left_border'] = None
        path['right_border'] = None
        return path
    num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(path)
    node_coordinates = [(nodes_dict[n]['x'], nodes_dict[n]['y']) for n in path['nodes']]
    path['right_border'] = shift_list_of_nodes(node_coordinates, [width*num_of_trunk_lanes/2.0]*len(node_coordinates))
    path['left_border'] = shift_list_of_nodes(node_coordinates, [-width*num_of_trunk_lanes/2.0] * len(node_coordinates))
    return path


def add_borders_to_paths(paths, nodes_dict, width=3.048):
    """
    Add borders to each of paths in the list.
    :param paths: list of dictionaries
    :param nodes_dict: dictionary
    :param width: float
    :return: list of dictionaries
    """
    for p in paths:
        add_borders_to_path(p, nodes_dict, width=width)
    return paths

def split_bidirectional_path(path):
    """
    Split a bidirectional path to two oneway paths
    :param path: dictionary
    :return: a tuple of dictionaries: forward and backward paths
    """

    if 'oneway' in path['tags'] and path['tags']['oneway'] == 'yes':
        return path, None

    forward_path = copy.deepcopy(path)
    forward_path['tags']['oneway'] = 'yes'
    forward_path['id'] = forward_path['id']*1000
    if 'turn:lanes:forward' in forward_path['tags']:
        forward_path['tags']['turn:lanes'] = forward_path['tags']['turn:lanes:forward']
    if 'turn:lanes:both_ways' in forward_path['tags']:
        forward_path['tags']['turn:lanes'] = forward_path['tags']['turn:lanes:both_ways']
    if 'lanes:forward' in forward_path['tags']:
        forward_path['tags']['lanes'] = forward_path['tags']['lanes:forward']

    backward_path = copy.deepcopy(path)
    backward_path['id'] = backward_path['id'] * 1000 + 1
    backward_path['tags']['oneway'] = 'yes'
    backward_path['nodes'] = backward_path['nodes'][::-1]
    if 'turn:lanes:forward' in forward_path['tags']:
        forward_path['tags']['turn:lanes'] = forward_path['tags']['turn:lanes:forward']
    if 'turn:lanes:both_ways' in forward_path['tags']:
        forward_path['tags']['turn:lanes'] = forward_path['tags']['turn:lanes:both_ways']
    if 'lanes:forward' in forward_path['tags']:
        forward_path['tags']['lanes'] = forward_path['tags']['lanes:forward']
    if 'destination:ref:backward' in forward_path['tags']:
        forward_path['tags']['destination:ref'] = forward_path['tags']['destination:ref:backward']
    if 'destination:backward' in forward_path['tags']:
        forward_path['tags']['destination'] = forward_path['tags']['destination:backward']

    return forward_path, backward_path


def split_bidirectional_paths(paths):
    """
    Replace bidirectional paths with oneway ones and return a new list
    :param paths: list of dictionaries
    :return: list of dictionaries
    """
    split = []
    for p in paths:
        forward_path, backward_path = split_bidirectional_path(p)
        split.append(forward_path)
        if backward_path is not None:
            split.append(backward_path)

    return split


def remove_nodes_without_coordinates(path, nodes_dict):
    path['nodes'] = [n for n in path['nodes'] if n in nodes_dict]
    return path


