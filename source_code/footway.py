#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for footways and crosswalks
#
#######################################################################


import copy
from lane import add_node_tags_to_lane, insert_referenced_nodes
from border import shift_list_of_nodes, shift_vector, get_compass, get_compass_rhumb, \
    extend_origin_border, extend_vector, get_closest_point, shift_by_bearing_and_distance, \
    get_line_intersection, cut_border_by_point, get_border_length, get_distance_between_points
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

    if crosswalk['left_border'] is not None:
        crosswalk['median'] = shift_list_of_nodes(crosswalk['left_border'],
                                                  [width / 2.0] * len(crosswalk['left_border']))
    else:
        crosswalk['median'] = None

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
    """
    Check if the crosswalk intersects the street
    :param crosswalk: crosswalk dictionary
    :param street_data: street dictionary
    :return: True or False
    """
    vector = [street_data['right_border'][-1], street_data['left_border'][-1]]
    polygon = geom.Polygon(vector + shift_vector(vector, -100)[::-1])
    line = geom.LineString(crosswalk['median'])
    return line.intersects(polygon)


def crosswalk_intersects_median(crosswalk, median):
    """
    Check if crosswalk's median intersects another median from a different object
    :param crosswalk: crosswalk dictionary
    :param median: list of coordinates
    :return: True or False
    """
    line = geom.LineString(crosswalk['median'])
    return geom.LineString(median).intersects(line)


def get_crosswalk_to_crosswalk_distance(crosswalk1, crosswalk2, median):
    """
    Get the distance between two crosswalk along a median line of a guideway.
    It assumed that the crosswalks intersects the median.  Returns -1 otherwise.
    :param crosswalk1: crosswalk dictionary
    :param crosswalk2: crosswalk dictionary
    :param median: list of coordinates
    :return: 
    """

    dist = [-1]
    border_types = ['left_border', 'right_border']
    try:
        start_points = [get_line_intersection(crosswalk1[b], median) for b in border_types]
        end_points = [get_line_intersection(crosswalk2[b], median) for b in border_types]
        for start in start_points:
            if start is None:
                continue
            for end in end_points:
                if end is None:
                    continue

                m1 = cut_border_by_point(median, start, ind=-1)
                m2 = cut_border_by_point(m1, end, ind=0)
                dist.append(get_border_length(m2))
    except Exception as e:
        logger.error('Failed to calculate distance between crosswalks')
        logger.error('First crosswalk: %s, %s' % (crosswalk1['name'], crosswalk1['compass']))
        logger.error('First crosswalk: %s, %s' % (crosswalk2['name'], crosswalk2['compass']))
        logger.exception('%r' % e)

    return max(dist)


def is_highway(street_data):
    if "tags" in street_data and "highway" in street_data["tags"] and "motorway" in \
            street_data["tags"]["highway"]:
        return True
    return False


def crossing_highway(f, streets):
    if "simulated" not in f:
        return False
    if f['simulated'] != 'yes':
        return False
    for s in streets:
        if f["name"] == s["name"]:
            if "tags" in s and "highway" in s["tags"] and "motorway" in s["tags"]["highway"]:
                return True
    return False


def remove_crossing_over_highway(x):
    return [c for c in x['crosswalks'] if not crossing_highway(c, x['street_data'])]


def get_simulated_crosswalk(street_data, streets, width=1.8):
    """
    Construct a simulated crosswalk
    :param street_data: street dictionary
    :param streets: list of dictionaries
    :param width: float, crosswalk width in meters
    :return: crosswalk dictionary
    """
    if is_highway(street_data):
        return None
    logger.debug("Simulated crosswalk for %s" % street_data['name'])
    right_border = shorten_border_for_crosswalk(street_data['right_border'],
                                                street_data['name'],
                                                streets,
                                                crosswalk_width=3,
                                                destination='to_intersection',
                                                exclude_parallel=True,
                                                max_reduction=130.0
                                                )
    left_border = shorten_border_for_crosswalk(street_data['left_border'],
                                               street_data['name'],
                                               streets,
                                               crosswalk_width=3,
                                               destination='to_intersection',
                                               exclude_parallel=True,
                                               max_reduction=130.0
                                               )

    right_border2 = shorten_border_for_crosswalk(street_data['right_border'],
                                                 street_data['name'],
                                                 streets,
                                                 crosswalk_width=3 + width,
                                                 destination='to_intersection',
                                                 exclude_parallel=True,
                                                 max_reduction=130.0
                                                 )

    left_border2 = shorten_border_for_crosswalk(street_data['left_border'],
                                                street_data['name'],
                                                streets,
                                                crosswalk_width=3 + width,
                                                destination='to_intersection',
                                                exclude_parallel=False,
                                                max_reduction=130.0
                                                )

    vector = [right_border[-1], right_border2[-1]]
    resized_vector = extend_vector(vector, length=width, backward=False)
    vector2 = [get_closest_point(p, street_data['left_border']) for p in resized_vector]
    # logger.debug("Vector %r" % vector)
    # logger.debug("Resize %r" % resized_vector)
    # logger.debug("Vecto2 %r" % vector2)
    r_b = [right_border[-1], left_border[-1]]
    r_l = [shift_by_bearing_and_distance(r_b[0], width, [right_border[-1], right_border[-2]],
                                         bearing_delta=0.0),
           shift_by_bearing_and_distance(r_b[-1], width, [left_border[-1], left_border[-2]],
                                         bearing_delta=0.0)]
    crosswalk = {
        'lane_id': '1C',
        'name': street_data['name'],
        'simulated': 'yes',
        # 'right_border': [vector[0], vector2[0]],
        # 'left_border': [resized_vector[1], vector2[1]],
        'right_border': r_b,  # [right_border[-1], left_border[-1]],
        'left_border': r_l,  # [right_border2[-1], left_border2[-1]],
        'median': shift_vector([right_border[-1], left_border[-1]], -width / 2.0),
        'path_id': 0,
        'path': [],
        'lane_type': 'crosswalk',
        'direction': 'undefined',
        'nodes': [],
        'nodes_coordinates': [],
        'width': width,
        'type': 'footway'
    }
    bearing = get_compass(crosswalk['right_border'][0], crosswalk['right_border'][-1])
    crosswalk['bearing'] = bearing
    crosswalk['compass'] = get_compass_rhumb(bearing),
    crosswalk['length'] = get_border_length(crosswalk['median'])
    if crosswalk['length'] > 50.0:
        return None
    if "id" in street_data:
        crosswalk["street_id"] = street_data["id"]
    logger.debug(
        'Created crosswalk for street %s %s' % (street_data['name'], street_data['compass']))

    return crosswalk


def get_simulated_crosswalks(streets, crosswalks, width=1.8):
    """
    Get a list of simulated crosswalks
    :param streets: list of street dictionaries
    :param crosswalks: list of real crosswalks dictionaries
    :param width: float in meters
    :return: list of simulated crosswalks dictionaries
    """
    simulated_crosswalks = []
    for street_data in streets:
        try:
            if crosswalks and any(
                    [crosswalk_intersects_street(c, street_data) for c in crosswalks]):
                logger.debug('Crosswalk exists for street %s %s' % (
                    street_data['name'], street_data['compass']))
                continue
            simulated = get_simulated_crosswalk(street_data, streets, width=width)
            if simulated is not None:
                simulated_crosswalks.append(simulated)
        except Exception as e:
            logger.exception('Street %s causing crosswalk exception %r' % (street_data['name'], e))
            continue
    return simulated_crosswalks


def remove_intersecting_portion_from_streets(street_data, streets):
    """
    Cut out intersecting portions of streets with the specified street.
    Reserved for future use
    :param street_data: street dictionary
    :param streets: list of dictionaries
    :return: list of dictionaries
    """
    streets_without_intersection = []
    for st in streets:
        if street_data['name'] == st['name'] or 'link' in st['name']:
            continue
        shorten_street = copy.deepcopy(st)
        right_border = shorten_border_for_crosswalk(st['right_border'],
                                                    st['name'],
                                                    streets,
                                                    crosswalk_width=20,
                                                    destination='to_intersection'
                                                    )
        left_border = shorten_border_for_crosswalk(st['left_border'],
                                                   st['name'],
                                                   streets,
                                                   crosswalk_width=20,
                                                   destination='to_intersection'
                                                   )
        shorten_street['right_border'] = extend_origin_border(right_border, relative=True)
        shorten_street['left_border'] = extend_origin_border(left_border, relative=True)
        streets_without_intersection.append(shorten_street)

    return streets_without_intersection


def reset_simulated_crosswalks(x):
    without_sim = [c for c in x["crosswalks"] if "simulated" not in c or c["simulated"] != "yes"]
    x['crosswalks'] = without_sim + get_simulated_crosswalks(x['street_data'], without_sim)


def insert_distances_to_the_center(x):
    center = (x["center_x"], x["center_y"])
    for c in x["crosswalks"]:
        c["distance_to_center"] = min(
            [get_distance_between_points(center, p) for p in c["right_border"] + c["left_border"]])
