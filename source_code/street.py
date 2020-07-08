#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for streets
#
#######################################################################


import copy
from border import get_distance_between_nodes, get_compass_rhumb, get_border_length, get_lane_bearing, \
    get_distance_from_point_to_line
from turn import shorten_border_for_crosswalk
from railway import split_track_by_node_index
from lane import get_most_right_lane, get_most_left_lane, get_sorted_lane_subset, get_lane_index_from_right, \
    get_lane_index_from_left
from log import get_logger


logger = get_logger()


def insert_street_names(city_data):
    """
    Insert street names into each node in the city data structure
    :param city_data: dictionary
    :return: dictionary
    """
    for p_d in city_data['paths']:
        if 'tags' in p_d and 'railway' not in p_d['tags'] and 'name' in p_d['tags'] and p_d['tags']['name'] != 'no_name':
            for node_id in p_d['nodes']:
                if 'street_name' not in city_data['nodes'][node_id]:
                    city_data['nodes'][node_id]['street_name'] = set()
                city_data['nodes'][node_id]['street_name'].add(p_d['tags']['name'])

    return city_data


def add_street_names_to_nodes(paths, nodes_dict):
    """
     Insert street names into each node
     :param paths: list of path dictionaries
     :param nodes_dict: node dictionary
     :return: None
     """
    for p_d in paths:
        if 'tags' in p_d and 'railway' not in p_d['tags'] and 'name' in p_d['tags'] and p_d['tags']['name'] != 'no_name':
            for node_id in p_d['nodes']:
                if 'street_name' not in nodes_dict[node_id]:
                    nodes_dict[node_id]['street_name'] = set()
                nodes_dict[node_id]['street_name'].add(p_d['tags']['name'])


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
    :param streets: list of street dictionaries
    :return: list of dictionaries
    """

    split_paths = []
    split_occurred = False
    for path_data in paths:
        cut_flag = 'no'
        if 'name' in path_data['tags'] and path_data['tags']['name'] in streets:
            for i, n in enumerate(path_data['nodes']):
                if 0 < i < len(path_data['nodes']) - 1 and 'street_name' in nodes_dict[n] \
                        and len(nodes_dict[n]['street_name']) > 1:
                    if len([s for s in nodes_dict[n]['street_name']]) > 1:
                        path1, path2 = split_track_by_node_index(path_data, i)
                        cut_flag = 'yes'
                        split_paths.append(path1)
                        split_paths.append(path2)
                        split_occurred = True
                        logger.debug("Cut path %r into %r and %r" % (path_data['id'], path1['id'], path2['id']))
                        logger.debug("Cut %s by node %r" % (path_data['tags']['name'], n))
                        break

        if cut_flag == 'no':
            split_paths.append(path_data)

    return split_paths, split_occurred


def repeat_street_split(paths, nodes_dict, streets, n=20):
    """
    Repeat path splitting
    :param paths: list of paths dictionaries
    :param nodes_dict: dictionary of all nodes
    :param streets: list of street dictionaries
    :param n: number of iterations
    :return: list of paths dictionaries
    """

    split_paths = copy.deepcopy(paths)
    for i in range(n):
        split_paths, split_occurred = split_streets(split_paths, nodes_dict, streets)
        if not split_occurred:
            break
    return split_paths


def get_lanes_close_to_the_intersection(x_data, crosswalk_width=1.82):
    """
    Get a subset of lanes that are adjacent to the intersection center for construction of crosswalks.
    Lanes that ends at a distance to the center are excluded.
    :param lanes: 
    :param crosswalk_width: 
    :return: list of lane dictionaries
    """
    close_lanes = []
    for lane_data in x_data['merged_lanes']:
        if [n for n in lane_data['nodes'] if n in x_data['x_nodes']]:
            close_lanes.append(lane_data)
            continue
        dist = get_distance_from_point_to_line((x_data['center_x'], x_data['center_y']), lane_data['median'])
        logger.debug("Distance from center to %d %s is %r" % (lane_data['id'], lane_data['name'], dist))

        if dist < 4*crosswalk_width:
            close_lanes.append(lane_data)
            continue

        median = shorten_border_for_crosswalk(lane_data['median'],
                                              lane_data['name'],
                                              x_data['merged_lanes'],
                                              crosswalk_width=5*crosswalk_width,
                                              destination=lane_data['direction']
                                              )
        if get_border_length(median) < lane_data['length']:
            close_lanes.append(lane_data)
    return close_lanes


def get_street_by_name_and_bearing(lanes, name, bearing):
    """
    Create a street dictionary based name and compass bearing.
    The bearing does not need to be accurate
    :param lanes: list of lane dictionaries
    :param name: string
    :param bearing: float in degrees
    :return: street dictionary
    """
    if bearing is None:
        logger.warning('Undefined bearing %s %r' % (name, bearing))
        return None

    opposite = (bearing + 180.0) % 360.0
    if 'link' in name:
        from_subset = []
    else:
        from_subset = get_sorted_lane_subset(lanes, name, opposite, 'from_intersection', get_lane_index_from_right)

    to_subset = get_sorted_lane_subset(lanes, name, bearing, 'to_intersection', get_lane_index_from_left)
    border_list = []

    for lane_data in from_subset:
        border_list.append(lane_data['right_border'][::-1])
        border_list.append(lane_data['left_border'][::-1])
    for lane_data in to_subset:
        border_list.append(lane_data['left_border'])
        border_list.append(lane_data['right_border'])

    if len(border_list) == 0:
        logger.debug('Failed to create street %s %r' % (name, bearing))
        return None

    right_border = border_list[-1]
    left_border = border_list[0]
    lane_ids = [l['id'] for l in from_subset + to_subset]

    if from_subset and to_subset:
        street_direction = 'both'
    elif to_subset:
        street_direction = 'to_intersection'
    else:
        street_direction = 'from_intersection'

    street_data = {
        'name': name,
        'direction': street_direction,
        'right_border': right_border,
        'left_border': left_border,
        'lane_ids': lane_ids
    }

    street_data['bearing'] = get_lane_bearing(street_data)
    street_data['compass'] = get_compass_rhumb(street_data['bearing'])
    logger.debug('Created %s %s %r' % (name, street_data['compass'], bearing))
    return street_data


def insert_tags_to_streets(x):
    streets = x["street_data"]
    all_lanes = x["merged_lanes"]
    for s in streets:
        if "tags" not in s:
            s["tags"] = {}
        for l in all_lanes:
            if l["id"] in s["lane_ids"] and "path" in l:
                for p in l["path"]:
                    if "tags" in p:
                        for t in p["tags"]:
                            s["tags"][t] = p["tags"][t]


def get_street_names_from_lanes(lanes):
    """
    Get a set of street names from all lanes
    :param lanes: list of lane dictionaries
    :return: set of strings
    """
    return set([l['name'] for l in lanes])


def get_to_intersection_bearing(lanes, name):
    """
    Identify compass bearing towards the intersection for a street name 
    regardless of whether any lanes exists in the direction
    :param lanes: list of lane dictionaries
    :param name: string
    :return: float in degrees
    """
    bearings = [l['bearing'] for l in lanes if l['name'] == name and l['direction'] == 'to_intersection']
    if bearings:
        return bearings[0]
    bearings = [l['bearing'] for l in lanes if l['name'] == name and l['direction'] == 'from_intersection']
    if bearings:
        return (bearings[0] + 180.0) % 360.0
    return None


def get_list_of_streets(x_data):
    """
    Get list of street dictionaries.  
    Definition of a street: combined area of lanes with same street name, 
    possibly in both directions, at one side of the intersection
    :param lanes: list of lane dictionaries
    :return: list of street dictionaries
    """
    close_lanes = get_lanes_close_to_the_intersection(x_data)
    if len(close_lanes) == 0:
        logger.warning('List of close lanes is empty')

    list_of_street_data = []
    for name in get_street_names_from_lanes(close_lanes):
        bearing = get_to_intersection_bearing(close_lanes, name)
        if bearing is None:
            logger.warning('Bearing is None %s' % name)
            continue

        street_data = get_street_by_name_and_bearing(close_lanes, name, bearing)
        if street_data is not None:
            list_of_street_data.append(street_data)
        else:
            logger.warning('Street %s is None' % name)

        street_data = get_street_by_name_and_bearing(close_lanes, name, (bearing + 180.0) % 360.0)
        if street_data is not None:
            list_of_street_data.append(street_data)
        else:
            logger.debug('Opposite street %s is None' % name)

    insert_street_ids(list_of_street_data)
    return sorted(list_of_street_data, key=lambda p: p['name'] + p['compass'])


def insert_street_ids(streets):
    for i,s in enumerate(streets):
        s["id"] = i
