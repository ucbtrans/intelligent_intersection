#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for streets
#
#######################################################################

from border import get_distance_between_nodes


def insert_street_names(city):
    """
    Insert street names into each node dictionary in the city data structure
    :param city: dictionary
    :return: dictionary
    """
    for path in city['paths']:
        if 'name' in path['tags'] and path['tags']['name'] != 'no_name':
            for node in path['nodes']:
                if 'street_name' not in city['nodes'][node]:
                    city['nodes'][node]['street_name'] = set()
                city['nodes'][node]['street_name'].add(path['tags']['name'])

    return city


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


def get_adjacent_streets(node, nodes_dict):
    """
    Get all streets within a short distance from the given node
    :param node: dictionary
    :param nodes_dict: dictionary
    :return: tupple of street names
    """
    streets = []
    for n in select_close_nodes(nodes_dict, [node]):
        if 'street_name' in n:
            streets.extend(list(n['street_name']))
    return sorted(list(set(streets)))
