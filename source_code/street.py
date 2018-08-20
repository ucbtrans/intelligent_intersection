#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for streets
#
#######################################################################


from border import get_distance_between_nodes
from railway import split_track_by_node_index


def insert_street_names(city_data):
    """
    Insert street names into each node in the city data structure
    :param city_data: dictionary
    :return: dictionary
    """
    for path_data in city_data['paths']:
        if 'name' in path_data['tags'] and path_data['tags']['name'] != 'no_name':
            for node_id in path_data['nodes']:
                if 'street_name' not in city_data['nodes'][node_id]:
                    city_data['nodes'][node_id]['street_name'] = set()
                city_data['nodes'][node_id]['street_name'].add(path_data['tags']['name'])

    return city_data


def add_street_names_to_nodes(paths, nodes_dict):
    """
     Insert street names into each node
     :param paths: list of path dictionaries
     :param nodes_dict: node dictionary
     :return: None
     """
    for path in paths:
        if 'name' in path['tags'] and path['tags']['name'] != 'no_name':
            for node_id in path['nodes']:
                if 'street_name' not in nodes_dict[node_id]:
                    nodes_dict[node_id]['street_name'] = set()
                nodes_dict[node_id]['street_name'].add(path['tags']['name'])


def select_close_nodes(nodes_d, nodes, too_far=50.0):
    """
    Get all nodes within a short distance of the input list of nodes.
    The current version takes only the first node in the list ignoring the rest.
    :param nodes_d: dictionary
    :param nodes: dictionary
    :param too_far: float distance in meters
    :return: set of dictionaries
    """
    if len(nodes) < 1:
        return None

    first_node = list(nodes)[0]
    return set([n for n in nodes if get_distance_between_nodes(nodes_d, first_node, n) <= too_far])


def get_adjacent_streets(node_data, nodes_dict):
    """
    Get all streets within a short distance from the given node
    :param node_data: dictionary
    :param nodes_dict: dictionary
    :return: tupple of street names
    """
    streets = []
    for n in select_close_nodes(nodes_dict, [node_data]):
        if 'street_name' in n:
            streets.extend(list(n['street_name']))
    return sorted(list(set(streets)))


def get_intersections_for_a_street(street_data, intersecting_streets):
    """
    Takes two parameters: a list of intersecting streets and a street name.
    Returns a subset of intersecting streets where the given street is a part of.
    :param street_data: string
    :param intersecting_streets: list of tuples
    :return: set of dictionaries
    """
    result = set()
    for x in intersecting_streets:
        for s in x:
            if street_data in s:
                result.add(x)
                break
    return result


def split_streets(paths, nodes_dict, streets):
    """
    Split paths in the list into pieces if they intersect with a street not at the end or beginning.
    Intersecting means a node belonging to two or more streets which form the intersection.
    :param paths: list of dictionaries
    :param nodes_dict: dictionary of all nodes
    :return: list of dictionaries
    """

    split_paths = []

    for path_data in [p for p in paths if 'name' in p['tags'] and p['tags']['name'] in streets]:
        split = 'no'
        for i, n in enumerate(path_data['nodes']):
            if 0 < i < len(path_data['nodes']) - 1 and 'street_name' in nodes_dict[n] \
                    and len(nodes_dict[n]['street_name']) > 1:
                if len([s for s in nodes_dict[n]['street_name'] if s in streets]) > 1:
                    path1, path2 = split_track_by_node_index(path_data, i)
                    split = 'yes'
                    path1['tags']['split'] = 'yes'
                    path2['tags']['split'] = 'yes'
                    split_paths.append(path1)
                    split_paths.append(path2)
                    break
        path_data['tags']['split'] = split

    split_paths.extend([t for t in paths if 'split' not in  t['tags'] or t['tags']['split'] == 'no'])
    return split_paths


def repeat_street_split(paths, nodes_dict, n=2):
    """
    Repeat path splitting
    :param paths: list of paths dictionaries
    :param nodes_dict: dictionary of all nodes
    :param n: number of iterations
    :return: list of paths dictionaries
    """

    split_paths = paths
    for i in range(n):
        split_paths = split_streets(split_paths, nodes_dict)
    return split_paths
