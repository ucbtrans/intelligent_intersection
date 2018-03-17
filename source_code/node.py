#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides node level functions
#
#######################################################################


def get_nodes_dict(city_paths_nodes):
    """
    Parse nodes from an osm response and convert them into the osmnx format
    :param city_paths_nodes: list of dictinaries
    :return: list of dictionaries
    """
    nodes = {}
    for city_paths_node in city_paths_nodes:
        for element in city_paths_node['elements']:
            if element['type'] == 'node':
                key = element['id']
                nodes[key] = get_node(element)

    return nodes


def get_node(element):
    """
    Convert an OSM node element into the format for a networkx node mathcing the osmnx data format
    :param element: dictionary: osm element
    :return: dictionary representing a node
    """

    node_data = {
        'y': element['lat'],
        'x': element['lon'],
        'osmid': element['id']
        }

    if 'tags' in element:
        for tag in element['tags']:
            node_data[tag] = element['tags'][tag]

    return node_data


def get_nodes_ids_for_street(paths, name):
    """
    Get a list of node ids realted to a street
    :param paths: list of dictionaries
    :param name: string
    :return: list of node ids
    """
    node_ids = []
    for path_data in [p for p in paths if 'name' in p['tags'] and name in p['tags']['name']]:
        node_ids.extend(path_data['nodes'])
    return set(node_ids)


def get_node_subset(city_paths_nodes, section):
    section_nodes = []
    [section_nodes.extend(p['nodes']) for p in section]
    section_node_set = set(section_nodes)
    return [n for n in city_paths_nodes[0]['elements'] if n['type'] == 'node' and n['id'] in section_node_set]


def get_intersection_nodes(paths, street_tuple):
    """
    Get node ids for an intersection.  The intersection is defines by a tuple of intersectiong streets.
    :param paths: list of dictionaries
    :param street_tuple: tuple of strings
    :return: set of node ids
    """

    node_ids = get_nodes_ids_for_street(paths, street_tuple[0])

    for street in street_tuple[1:]:
        node_ids = node_ids & get_nodes_ids_for_street(paths, street)
    return node_ids


def get_center(nodes, nodes_d):
    """
    Calculate the center of an intersection
    :param nodes: list of node ids
    :param nodes_d: node dictionary
    :return: tuple of floats
    """
    if len(nodes) < 1:
        return None

    x = sum([nodes_d[n]['x'] for n in nodes]) / len(nodes)
    y = sum([nodes_d[n]['y'] for n in nodes]) / len(nodes)

    return x, y
