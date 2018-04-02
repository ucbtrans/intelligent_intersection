#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides path level functions
#
#######################################################################

from border import shift_list_of_nodes, shift_border, get_compass_bearing, get_compass_rhumb
import copy
import osmnx as ox


def get_num_of_lanes(path_data):
    """
    Get the number of lanes from path
    :param path_data: dictionary
    :return: integer
    """
    # u'turn:lanes:forward': u'left;through|right'
    # u'lanes': u'3',
    # u'lanes:backward': u'1',
    # u'lanes:forward': u'2',
    # "u'lanes:forward'"

    if 'turn:lanes' in path_data['tags']:
        return len(path_data['tags']['turn:lanes'].split('|'))
    if 'lanes' in path_data['tags']:
        return int(path_data['tags']['lanes'])

    return 1


def count_lanes(path_data):
    """
    Calculate the number of left, right and trunk lanes
    :param path_data: dictionary
    :return: tuple of three integers: num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes
    """

    num_of_lanes = get_num_of_lanes(path_data)

    if 'turn:lanes' in path_data['tags']:
        lane_types = path_data['tags']['turn:lanes'].split('|')
    elif 'railway' in path_data['tags']:
        lane_types = ['rail_track'] * num_of_lanes
    else:
        lane_types = [''] * num_of_lanes

    lane_types = lane_types[::-1]
    num_of_left_lanes = lane_types.count('left')
    num_of_right_lanes = lane_types.count('right')
    num_of_trunk_lanes = num_of_lanes - num_of_left_lanes - num_of_right_lanes

    return num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes


def add_borders_to_path(path_data, nodes_dict, width=3.048):
    """
    Create left and right borders for a path assuming the path nodes defines the center of the street
    :param path_data: dictionary
    :param nodes_dict: dictionary
    :param width: float lane width in meters
    :return: dictionary
    """

    path_data = remove_nodes_without_coordinates(path_data, nodes_dict)
    if len(path_data['nodes']) < 2:
        path_data['left_border'] = None
        path_data['right_border'] = None
        return path_data
    num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(path_data)
    node_coordinates = [(nodes_dict[n]['x'], nodes_dict[n]['y']) for n in path_data['nodes']]

    if 'left_border' not in path_data or path_data['left_border'] is None:
        path_data['right_border'] = shift_list_of_nodes(node_coordinates,
                                                        [width*num_of_trunk_lanes/2.0]*len(node_coordinates)
                                                        )
        path_data['left_border'] = shift_list_of_nodes(node_coordinates,
                                                       [-width*num_of_trunk_lanes/2.0] * len(node_coordinates)
                                                       )
    else:
        path_data['right_border'] = shift_list_of_nodes(path_data['left_border'],
                                                        [width * num_of_trunk_lanes] * len(node_coordinates)
                                                        )
    return path_data


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


def split_bidirectional_path(path_data, nodes_dict, space_between_direction=1.0):
    """
    Split a bidirectional path to two oneway paths
    :param path_data: dictionary
    :param nodes_dict: dictionary
    :param space_between_direction: float in meters
    :return: a tuple of dictionaries: forward and backward paths
    """

    if 'oneway' in path_data['tags'] and path_data['tags']['oneway'] == 'yes':
        path_data['tags']['split'] = 'no'
        return path_data, None

    forward_path = copy.deepcopy(path_data)
    forward_path['tags']['split'] = 'yes'
    forward_path['tags']['oneway'] = 'yes'
    forward_path['id'] = forward_path['id']*1000
    if 'turn:lanes:forward' in forward_path['tags']:
        forward_path['tags']['turn:lanes'] = forward_path['tags']['turn:lanes:forward']
    if 'turn:lanes:both_ways' in forward_path['tags']:
        forward_path['tags']['turn:lanes'] = forward_path['tags']['turn:lanes:both_ways']
    if 'lanes:forward' in forward_path['tags']:
        forward_path['tags']['lanes'] = forward_path['tags']['lanes:forward']

    # process bicycle lanes
    if 'bicycle' not in forward_path['tags'] or forward_path['tags']['bicycle'] == 'yes':
        if 'cycleway:left' in forward_path:
            del forward_path['cycleway:left']
        if 'cycleway:both' in forward_path['tags']:
            forward_path['tags']['cycleway:right'] = forward_path['tags']['cycleway:both']
            del forward_path['tags']['cycleway:both']

    forward_path['left_border'] = shift_border(forward_path, nodes_dict, space_between_direction/2.0)

    backward_path = copy.deepcopy(path_data)
    backward_path['tags']['split'] = 'yes'
    backward_path['id'] = backward_path['id'] * 1000 + 1
    backward_path['tags']['oneway'] = 'yes'
    backward_path['nodes'] = backward_path['nodes'][::-1]

    if 'turn:lanes:backward' in forward_path['tags']:
        backward_path['tags']['turn:lanes'] = forward_path['tags']['turn:lanes:backward']
    if 'turn:lanes:both_ways' in forward_path['tags']:
        forward_path['tags']['turn:lanes'] = forward_path['tags']['turn:lanes:both_ways']
        backward_path['tags']['turn:lanes'] = forward_path['tags']['turn:lanes:both_ways']
    if 'lanes:backward' in forward_path['tags']:
        backward_path['tags']['lanes'] = forward_path['tags']['lanes:backward']
    if 'destination:ref:backward' in forward_path['tags']:
        backward_path['tags']['destination:ref'] = forward_path['tags']['destination:ref:backward']
    if 'destination:backward' in forward_path['tags']:
        backward_path['tags']['destination'] = forward_path['tags']['destination:backward']

    # process bicycle lanes
    if 'bicycle' not in backward_path['tags'] or backward_path['tags']['bicycle'] == 'yes':
        if 'cycleway:right' in backward_path:
            del backward_path['tags']['cycleway:right']
        if 'cycleway:left' in backward_path:
            backward_path['tags']['cycleway:right'] = backward_path['tags']['cycleway:left']
            del backward_path['tags']['cycleway:left']
        if 'cycleway:both' in backward_path['tags']:
            backward_path['tags']['cycleway:right'] = backward_path['tags']['cycleway:both']
            del backward_path['tags']['cycleway:both']

    backward_path['left_border'] = shift_border(backward_path, nodes_dict, space_between_direction / 2.0)

    return forward_path, backward_path


def split_bidirectional_paths(paths, nodes_dict):
    """
    Replace bidirectional paths with oneway ones and return a new list
    :param paths: list of dictionaries
    :param nodes_dict: dictionary
    :return: list of dictionaries
    """
    split = []
    for p in paths:
        forward_path, backward_path = split_bidirectional_path(p, nodes_dict)
        split.append(forward_path)
        if backward_path is not None:
            split.append(backward_path)

    return split


def remove_nodes_without_coordinates(path_data, nodes_dict):
    """
    Remove reference to nodes that are not in the input data
    :param path_data: dictionary
    :param nodes_dict: dictionary
    :return: dictionary
    """
    path_data['nodes'] = [n for n in path_data['nodes'] if n in nodes_dict]
    return path_data


def clean_paths(paths, street_tuple):
    """
    Remove streets not related to the current intersection
    :param paths: list of paths
    :param street_tuple: tuple of strings
    :return: cleaned list of paths
    """

    return [p for p in paths
            if ('name' in p['tags'] and (p['tags']['name'] in street_tuple))
            or ('highway' in p['tags'] and 'link' in p['tags']['highway'])
            ]


def remove_zero_length_paths(paths):
    """
    Remove paths having one node or no no node (zero length)
    :param paths: list of dictionaries
    :return: list of dictionaries
    """
    return [p for p in paths if 'nodes' in p and len(p['nodes']) > 1]


def set_direction(paths, x, y, nodes_dict):
    """
    Set direction relative to the intersection: to_intersection or from_intersection
    :param paths: list of dictionaries
    :param x: float
    :param y: float
    :param nodes_dict: dictionary
    :return: None
    """
    for p in paths:
        if len(p['nodes']) < 2 or ('highway' in p['tags'] and 'trunk_link' in p['tags']['highway']):
            p['tags']['direction'] = 'undefined'
            continue

        distance_to_center0 = ox.great_circle_vec(y, x, nodes_dict[p['nodes'][0]]['y'],
                                                  nodes_dict[p['nodes'][0]]['x'])
        distance_to_center1 = ox.great_circle_vec(y, x,
                                                  nodes_dict[p['nodes'][-1]]['y'],
                                                  nodes_dict[p['nodes'][-1]]['x']
                                                  )

        if distance_to_center0 > distance_to_center1:
            p['tags']['direction'] = 'to_intersection'
        else:
            p['tags']['direction'] = 'from_intersection'

        p['bearing'] = get_path_bearing(p, nodes_dict)
        p['compass'] = get_compass_rhumb(p['bearing'])


def get_path_bearing(path_data, nodes_dict):
    """
    Get compass bearing of a path
    :param path_data: dictionary
    :param nodes_dict: dictionary
    :return: float (degrees)
    """
    if 'nodes' not in path_data and len(path_data['nodes']) < 2:
        return None

    x0 = nodes_dict[path_data['nodes'][0]]['x']
    y0 = nodes_dict[path_data['nodes'][0]]['y']
    x1 = nodes_dict[path_data['nodes'][-1]]['x']
    y1 = nodes_dict[path_data['nodes'][-1]]['y']
    return get_compass_bearing((y0, x0), (y1, x1))


def reverse_direction(direction):
    """
    Reverse direction
    :param direction: string
    :return: string
    """
    if direction == 'to_intersection':
        return 'from_intersection'
    elif direction == 'from_intersection':
        return 'to_intersection'
    else:
        return direction
