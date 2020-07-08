#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides node level functions
#
#######################################################################


import copy
import time
from random import seed
from random import randint
from border import get_intersection_with_circle
from street import add_street_names_to_nodes

seed(int(time.time()*1000.0)%1000000)

def get_nodes_dict(city_paths_nodes, nodes_dict={}):
    """
    Parse nodes from an osm response and convert them into the osmnx format
    :param city_paths_nodes: list of dictionaries
    :param nodes_dict: dictionary
    :return: list of dictionaries
    """

    for city_paths_node in city_paths_nodes:
        for element in city_paths_node['elements']:
            if element['type'] == 'node':
                key = element['id']
                nodes_dict[key] = get_node(element)

    return nodes_dict


def get_node_dict_subset_from_list_of_lanes(lanes, nodes_dict, nodes_subset={}):
    """
    Create a subset of nodes dictionary for nodes referenced in the list of lanes
    :param lanes: list of dictionaries
    :param nodes_dict: dictionary
    :param nodes_subset: dictionary
    :return: dictionary
    """
    for lane_data in lanes:
        for n in lane_data['nodes']:
            if n in nodes_dict:
                nodes_subset[n] = nodes_dict[n]
    return nodes_subset


def get_node(element):
    """
    Convert an OSM node element into the format for a networkx node matching the osmnx data format
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
    for path_data in [p for p in paths if 'name' in p['tags'] and p['tags']['name'] == name]:
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
    result = []
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
    Get node ids for an intersection.  The intersection is defines by a tuple of intersecting streets.
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


def add_nodes_to_dictionary(nodes, nodes_dict, paths=None):
    """
    Add nodes to the node dictionary if missing
    :param nodes: list of nodes in the osm format
    :param nodes_dict: dictionary
    :param paths: list of path dictionaries
    :return: None
    """
    for n in nodes:
        if n['id'] not in nodes_dict:
            nodes_dict[n['id']] = get_node(n)

    if paths is not None:
        add_street_names_to_nodes(paths, nodes_dict)


def remove_nodes_outside_of_radius(node_list, nodes_dict, center, radius):
    """
    Remove nodes from list if outside of specified radius.
    Interpolate by creating intermediate nodes at the edge of the circle
    :param node_list: list of node ids
    :param nodes_dict: dictionary
    :param center: coordinates
    :param radius: float in meters
    :return: list of node ids
    """
    start_selection = 0
    end_selection = len(node_list)
    starting_node = None
    ending_node = None

    for i in range(1, len(node_list)):
        n0 = nodes_dict[node_list[i-1]]
        n1 = nodes_dict[node_list[i]]
        if n0['within_selection'] == 'no' and n1['within_selection'] == 'yes':
            start_selection = i
            starting_node = create_a_new_node_from_existing_one(n0, nodes_dict)
            vector = [(n1['x'], n1['y']), (n0['x'], n0['y'])]
            new_coord = get_intersection_with_circle(vector, center, radius)
            starting_node['x'] = new_coord[0]
            starting_node['y'] = new_coord[1]
        elif n0['within_selection'] == 'yes' and n1['within_selection'] == 'no':
            end_selection = i
            ending_node = create_a_new_node_from_existing_one(n1, nodes_dict)
            vector = [(n0['x'], n0['y']), (n1['x'], n1['y'])]
            new_coord = get_intersection_with_circle(vector, center, radius)
            ending_node['x'] = new_coord[0]
            ending_node['y'] = new_coord[1]

    if starting_node is not None:
        starting_list = [starting_node['osmid']]
    else:
        starting_list = []

    if ending_node is not None:
        ending_list = [ending_node['osmid']]
    else:
        ending_list = []

    return starting_list + node_list[start_selection:end_selection] + ending_list


def create_a_new_node_from_existing_one(node_data, nodes_dict, within_selection='yes'):
    """
    Create a new node from an existing one for interpolation purposes.
    The new node will have only osmid, within_selection, street_name if applicable
    :param node_data: dictionary
    :param nodes_dict: dictionary
    :param within_selection: 
    :return: dictionary
    """
    new_node = {'osmid': node_data['osmid'], 'within_selection': within_selection}
    if 'street_name' in node_data:
        new_node['street_name'] = copy.deepcopy(node_data['street_name'])
    for i in range(1, 1000000):
        new_id = node_data['osmid'] * 1000 + randint(0, 1000)
        if new_id not in nodes_dict:
            new_node['osmid'] = new_id
            break

    nodes_dict[new_id] = new_node

    return new_node


def create_a_node_from_coordinates(point, nodes_dict, street_name=None):
    """
    Create a new node from a point.
    :param point: tuple of coordinates
    :param nodes_dict: dictionary
    :param street_name: set of strings
    :return: dictionary
    """
    new_node = {'x': point[0], 'y': point[1], 'street_name': street_name}

    for i in range(1, 1000000):
        rand_id = randint(100000, 10000000)
        if rand_id not in nodes_dict:
            new_node['osmid'] = rand_id
            break

    nodes_dict[rand_id] = new_node

    return new_node
