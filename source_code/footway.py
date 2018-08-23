#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for footways
#
#######################################################################


from lane import add_node_tags_to_lane, insert_referenced_nodes
from border import shift_list_of_nodes, shift_vector, get_compass_rhumb
from turn import shorten_border_for_crosswalk
import shapely.geometry as geom


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
        'simulated': 'no',
        'path_id': path_data['id'],
        'bearing': path_data['bearing'],
        'compass': path_data['compass'],
        'path': [path_data],
        'lane_type': 'crosswalk',
        'direction': 'undefined',
        'nodes': path_data['nodes'],
        'nodes_coordinates': [(nodes_dict[n]['x'], nodes_dict[n]['y']) for n in path_data['nodes']],
        'width': width,
        'type': 'footway'
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

    crosswalk['median'] = shift_list_of_nodes(crosswalk['left_border'], [width / 2.0] * len(crosswalk['left_border']))

    add_node_tags_to_lane(crosswalk, nodes_dict)
    insert_referenced_nodes(crosswalk, nodes_dict)

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


def crosswalk_intersects_street(crosswalk, street_data):
    vector = [street_data['right_border'][-1], street_data['left_border'][-1]]
    polygon = geom.Polygon(vector + shift_vector(vector, -100)[::-1])
    line = geom.LineString(crosswalk['median'])
    return line.intersects(polygon)


def get_simulated_crosswalk(street_data, lanes, width=1.8):

    right_border = shorten_border_for_crosswalk(street_data['right_border'],
                                                street_data['name'],
                                                lanes,
                                                crosswalk_width=1,
                                                destination='to_intersection'
                                                )
    left_border = shorten_border_for_crosswalk(street_data['left_border'],
                                               street_data['name'],
                                               lanes,
                                               crosswalk_width=1,
                                               destination='to_intersection'
                                               )
    crosswalk = {
        'lane_id': '1C',
        'name': street_data['name'],
        'simulated': 'yes',
        'right_border': [right_border[-1], left_border[-1]],
        'left_border':  shift_vector([right_border[-1], left_border[-1]], -width),
        'median': shift_vector([right_border[-1], left_border[-1]], -width/2.0),
        'path_id': 0,
        'bearing': (street_data['bearing'] - 90.0) % 360.0,
        'compass': get_compass_rhumb((street_data['bearing'] - 90.0) % 360.0),
        'path': [],
        'lane_type': 'crosswalk',
        'direction': 'undefined',
        'nodes': [],
        'nodes_coordinates': [],
        'width': width,
        'type': 'footway'
    }

    return crosswalk


def get_simulated_crosswalks(streets, lanes, crosswalks, width=1.8):
    simulated_crosswalks = []
    for street_data in streets:
        if crosswalks and any([crosswalk_intersects_street(c, street_data) for c in crosswalks]):
            continue
        simulated_crosswalks.append(get_simulated_crosswalk(street_data, lanes, width=width))

    return simulated_crosswalks
