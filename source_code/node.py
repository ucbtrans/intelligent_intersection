#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides node level functions
#
#######################################################################


def get_nodes_dict(city_paths_nodes, nodes_dict={}):
    """
    Parse nodes from an osm response and convert them into the osmnx format
    :param city_paths_nodes: list of dictinaries
    :param nodes_dict: dictionary
    :return: list of dictionaries
    """

    for city_paths_node in city_paths_nodes:
        for element in city_paths_node['elements']:
            if element['type'] == 'node':
                key = element['id']
                nodes_dict[key] = get_node(element)

    return nodes_dict


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


def osmnx_to_osm(node_data):
    """
    Convert node from the osmnx format to the original osm one
    :param node_data: dictionary
    :return: dictionary
    """
    return {
        'lat': node_data['y'],
        'lon': node_data['x'],
        'id': node_data['osmid'],
        'type': 'node',
        'tags': {tag: node_data[tag] for tag in node_data if tag not in ['x', 'y', 'osmid']}
    }


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


def get_node_subset(city_paths_nodes, section, nodes_dict):
    """
    Filter out nodes not referenced in any path and possibly add missing nodes from the overall node dictionary
    :param city_paths_nodes: list of elements (paths and nodes)
    :param section: list of paths representing a subsection
    :param nodes_dict: dictionary
    :return: list of nodes
    """
    section_node_ids = []
    result =[]
    [section_node_ids.extend(p['nodes']) for p in section]
    section_node_set = set(section_node_ids)

    for n in city_paths_nodes[0]['elements']:
        if n['type'] != 'node':
            continue
        if n['id'] in section_node_set:
            result.append(n)

    for node_id in section_node_set - set([n['id'] for n in result]):
        if node_id in nodes_dict:
            result.append(osmnx_to_osm(nodes_dict[node_id]))

    return result


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


def add_nodes_to_dictionary(nodes, nodes_dict):
    """
    Add nodes to the node dictionary if missing
    :param nodes: list of nodes in the osm format
    :param nodes_dict: dictionary
    :return: None
    """
    for n in nodes:
        if n['id'] not in nodes_dict:
            nodes_dict[n['id']] = get_node(n)
