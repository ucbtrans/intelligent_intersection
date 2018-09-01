#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for streets
#
#######################################################################


from border import get_distance_between_nodes, get_compass_rhumb
from railway import split_track_by_node_index
from lane import get_most_right_lane, get_most_left_lane
from log import get_logger


logger = get_logger()


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
    elif len(nodes) == 1:
        return nodes

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


def get_intersections_for_a_street(street_name, intersecting_streets):
    """
    Takes two parameters: a list of intersecting streets and a street name.
    Returns a subset of intersecting streets where the given street is a part of.
    :param street_name: string
    :param intersecting_streets: list of tuples
    :return: set of dictionaries
    """
    result = set()
    for x in intersecting_streets:
        for s in x:
            if street_name in s:
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


def get_street_data_by_name_and_bearing(lanes, name, bearing):
    opposite_bearing = (bearing + 180.0) % 360.0
    logger.debug('Finding street boundaries for %s, bearings: %r %r' % (name, bearing, opposite_bearing))
    most_right_lane_to_intersection = get_most_right_lane(lanes, name, 'to_intersection', bearing)
    most_right_lane_from_intersection = get_most_right_lane(lanes, name, 'from_intersection', opposite_bearing)

    if most_right_lane_to_intersection is None and most_right_lane_from_intersection is None:
        logger.debug('No lanes found in either direction')
        return None
    elif most_right_lane_to_intersection is not None and most_right_lane_from_intersection is None:
        logger.debug('To intersection lane is OK. Most right lane from intersection not found')
        most_left_lane_to_intersection = get_most_left_lane(lanes, name, 'to_intersection', bearing)
        if most_left_lane_to_intersection is None:
            logger.debug('Most left lane to intersection not found')
            return None
        right_border = most_right_lane_to_intersection['right_border']
        left_border = most_left_lane_to_intersection['left_border']
        direction = 'to_intersection'
        to_id = most_right_lane_to_intersection['id']
        from_id = 0
    elif most_right_lane_to_intersection is None and most_right_lane_from_intersection is not None:
        logger.debug('From intersection lane is OK. Most right lane to intersection not found')
        most_left_lane_to_intersection = get_most_left_lane(lanes, name, 'from_intersection', opposite_bearing)
        if most_left_lane_to_intersection is None:
            logger.debug('Most left lane to intersection not found. Doublecheck this logic')
            return None
        right_border = most_right_lane_from_intersection['right_border'][::-1]
        left_border = most_left_lane_to_intersection['left_border'][::-1]
        direction = 'from_intersection'
        to_id = 0
        from_id = most_right_lane_from_intersection['id']
    else:
        logger.debug('Both directions found')
        right_border = most_right_lane_to_intersection['right_border']
        left_border = most_right_lane_from_intersection['right_border'][::-1]
        direction = 'both'
        from_id = most_right_lane_from_intersection['id']
        to_id = most_right_lane_to_intersection['id']

    street_data = {
        'name': name,
        'bearing': bearing,
        'compass': get_compass_rhumb(bearing),
        'direction': direction,
        'id': to_id*100 + from_id,
        'lane_id_to_intersection': to_id,
        'lane_id_from_intersection': from_id,
        'right_border': right_border,
        'left_border': left_border
    }

    return street_data


def get_street_names_from_lanes(lanes):
    return set([l['name'] for l in lanes])


def get_street_bearing(lanes, name, direction='to_intersection'):
    return [l['bearing'] for l in lanes if l['name'] == name and l['direction'] == direction]


def get_list_of_street_data(lanes):

    list_of_street_data = []
    for name in get_street_names_from_lanes(lanes):
        list_of_bearings = get_street_bearing(lanes, name, 'to_intersection')
        if list_of_bearings:
            bearing = list_of_bearings[0]
        else:
            list_of_bearings = get_street_bearing(lanes, name, 'from_intersection')
            if list_of_bearings:
                bearing = (list_of_bearings[0] + 180.0) % 360.0
            else:
                continue

        street_data = get_street_data_by_name_and_bearing(lanes, name, bearing)

        if street_data is not None:
            list_of_street_data.append(street_data)
        street_data = get_street_data_by_name_and_bearing(lanes, name, (bearing + 180.0) % 360.0)
        if street_data is not None:
            list_of_street_data.append(street_data)

    return list_of_street_data
