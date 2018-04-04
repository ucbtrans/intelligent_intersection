#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for footways
#
#######################################################################


def get_crosswalk_from_path(path_data, nodes_dict, width=1.8):
    """
    Create a crosswalk from a path.
    :param path_data: dictionary
    :param nodes_dict: dictionary
    :param width: float in meters
    :return: dictionary of crosswalk data
    """
    if 'highway' not in path_data['tags'] or 'foot' not in path_data['tags']['highway']:
        return None

    if 'footway' not in path_data['tags'] or 'crossing' not in path_data['tags']['footway']:
        return None

    crosswalk = {
        'lane_id': '1C',
        'path_id': path_data['id'],
        'bearing': path_data['bearing'],
        'compass': path_data['compass'],
        'path': [path_data],
        'lane_type': 'crosswalk',
        'direction': 'undefined',
        'nodes': path_data['nodes'],
        'nodes_coordinates': [(nodes_dict[n]['x'], nodes_dict[n]['y']) for n in path_data['nodes']],
        'width': width,
    }

    for x in path_data['tags']:
        crosswalk[x] = path_data['tags'][x]

    if 'name' not in path_data['tags']:
        crosswalk['name'] = 'no_name'

    if 'left_border' in path_data:
        crosswalk['left_border'] = path_data['left_border']
    else:
        crosswalk['left_border'] = None

    if 'right_border' in path_data:
        crosswalk['right_border'] = path_data['right_border']
    else:
        crosswalk['right_border'] = None

    return crosswalk


def get_crosswalks(paths, nodes_dict, width=1.8):
    """
    Create a list of crosswalks from a list of paths.
    :param paths: list of dictionaries
    :param nodes_dict: dictionary
    :param width: float in meters
    :return: list of dictionaries
    """
    crosswalks = []
    for p in paths:
        crosswalk = get_crosswalk_from_path(p, nodes_dict, width=width)
        if crosswalk is not None:
            crosswalks.append(crosswalk)
    return crosswalks
