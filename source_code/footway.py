#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for footways
#
#######################################################################


import copy
from lane import add_node_tags_to_lane, insert_referenced_nodes
from border import shift_list_of_nodes, shift_vector, get_compass, get_compass_rhumb, extend_origin_border
from turn import shorten_border_for_crosswalk
import shapely.geometry as geom
from log import get_logger, dictionary_to_log


logger = get_logger()


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


def get_simulated_crosswalk(street_data, streets, width=1.8):
    streets_without_intersection = remove_intersecting_portion_from_streets(street_data, streets)
    right_border = shorten_border_for_crosswalk(street_data['right_border'],
                                                street_data['name'],
                                                streets_without_intersection,
                                                crosswalk_width=2,
                                                destination='to_intersection'
                                                )
    left_border = shorten_border_for_crosswalk(street_data['left_border'],
                                               street_data['name'],
                                               streets_without_intersection,
                                               crosswalk_width=2,
                                               destination='to_intersection'
                                               )

    right_border2 = shorten_border_for_crosswalk(street_data['right_border'],
                                                 street_data['name'],
                                                 streets_without_intersection,
                                                 crosswalk_width=2 + width,
                                                 destination='to_intersection'
                                                 )
    left_border2 = shorten_border_for_crosswalk(street_data['left_border'],
                                                street_data['name'],
                                                streets_without_intersection,
                                                crosswalk_width=2 + width,
                                                destination='to_intersection'
                                                )
    bearing = get_compass(right_border[0], right_border[-1])
    crosswalk = {
        'lane_id': '1C',
        'name': street_data['name'],
        'simulated': 'yes',
        'right_border': [right_border[-1], left_border[-1]],
        'left_border': [right_border2[-1], left_border2[-1]],
        'old_left_border':  shift_vector([right_border[-1], left_border[-1]], -width),
        'median': shift_vector([right_border[-1], left_border[-1]], -width/2.0),
        'path_id': 0,
        'bearing': bearing,
        'compass': get_compass_rhumb(bearing),
        'path': [],
        'lane_type': 'crosswalk',
        'direction': 'undefined',
        'nodes': [],
        'nodes_coordinates': [],
        'width': width,
        'type': 'footway'
    }

    return crosswalk


def get_simulated_crosswalks(streets, crosswalks, width=1.8):
    simulated_crosswalks = []
    for street_data in streets:
        try:
            if crosswalks and any([crosswalk_intersects_street(c, street_data) for c in crosswalks]):
                continue
            simulated_crosswalks.append(get_simulated_crosswalk(street_data, streets, width=width))
        except Exception as e:
            logger.exception('Street %s causing crosswalk exception %r' % (street_data['name'], e))
            continue
    return simulated_crosswalks


def remove_intersecting_portion_from_streets(street_data, streets):
    streets_without_intersection = []
    for st in streets:
        if street_data['name'] == st['name'] or 'link' in st['name']:
            continue
        shorten_street = copy.deepcopy(st)
        right_border = shorten_border_for_crosswalk(st['right_border'],
                                                    st['name'],
                                                    streets,
                                                    crosswalk_width=10,
                                                    destination='to_intersection'
                                                    )
        left_border = shorten_border_for_crosswalk(st['left_border'],
                                                   st['name'],
                                                   streets,
                                                   crosswalk_width=10,
                                                   destination='to_intersection'
                                                   )
        shorten_street['right_border'] = extend_origin_border(right_border, relative=True)
        shorten_street['left_border'] = extend_origin_border(left_border, relative=True)
        streets_without_intersection.append(shorten_street)

    return streets_without_intersection
