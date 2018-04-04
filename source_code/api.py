#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides top level API routines
#
#######################################################################


import copy
import osmnx as ox
from intersection import get_intersection_data, plot_lanes
from street import insert_street_names, get_intersections_for_a_street
from guideway import get_left_turn_guideways, get_right_turn_guideways, plot_guideways, \
    get_through_guideways, set_guideway_ids
from city import get_city_name_from_address
from node import get_nodes_dict


def get_city(city_name, network_type="drive"):
    """
    Get street structure of a city
    :param city_name: city name like 'Campbell, California, USA'
    :param network_type: string: {'walk', 'bike', 'drive', 'drive_service', 'all', 'all_private', 'none'}
    :return: a tuple of list of paths and a nodes dictionary
    """
    city_paths_nodes = None
    for which_result in range(1, 4):
        try:
            city_boundaries = ox.gdf_from_place(city_name, which_result=which_result)
            city_paths_nodes = ox.osm_net_download(city_boundaries['geometry'].unary_union, network_type=network_type)
            break
        except ValueError:
            continue
    if city_paths_nodes is None:
        return None

    nodes_dict = get_nodes_dict(city_paths_nodes)
    paths = [p for p in city_paths_nodes[0]['elements'] if p['type'] != 'node']
    city_data = {
        'name': city_name,
        'paths': paths,
        'nodes': nodes_dict
    }
    return insert_street_names(city_data)


def get_streets(city_data):
    """
    Get set of streets from a city structure
    :param city_data: dictionary
    :return: return a set of street names
    """

    return set([p['tags']['name'] for p in city_data['paths'] if 'name' in p['tags']])


def get_intersecting_streets(city_data):
    """
    Get a list of intersecting street.  Each element is a tuple of two or more street names.
    :param city_data: dictionary
    :return: list of tuples
    """
    intersecting_streets = set()

    for node_id in city_data['nodes']:
        if 'street_name' in city_data['nodes'][node_id] and len(city_data['nodes'][node_id]['street_name']) > 1:
            intersecting_streets.add(tuple(sorted(list(city_data['nodes'][node_id]['street_name']))))

    duplicates = set()
    for x in intersecting_streets:
        if len(x) < 3:
            continue
        for st1 in x:
            for st2 in x:
                if st1 == st2:
                    continue
                if (st1, st2) in intersecting_streets:
                    duplicates.add((st1, st2))

                if len(x) < 3:
                    continue

                for st3 in x:
                    if st3 == st2 or st3 == st1:
                        continue
                    if (st1, st2, st3) in intersecting_streets:
                        duplicates.add((st1, st2, st3))

    return sorted(list(intersecting_streets - duplicates))


def get_intersection(street_tuple, city_data, size=500.0, crop_radius=150.0):
    """
    Get a dictionary with all data related to an intersection.
    :param street_tuple: tuple of strings
    :param city_data: dictionary
    :param size: initial size of the surrounding area in meters
    :param crop_radius: the data will be cropped to the specified radius in meters
    :return: dictionary
    """

    return get_intersection_data(street_tuple, city_data, size=size, crop_radius=crop_radius)


def get_intersections(list_of_addresses, size=500.0, crop_radius=150.0):
    """
    Get a list of intersections defined by their addresses, 
    e.g. ["San Pablo and University, Berkeley, California", "Van Ness and Geary, San Francisco, Califocrnia", ...]
    Please spell out California instead of CA, because CA can be interpreted as Canada
    :param list_of_addresses: list of strings
    :param size: float in meters
    :param crop_radius: float in meters
    :return: list of dictionaries
    """

    cities = {}

    if not isinstance(list_of_addresses, list):
        list_of_addresses = [list_of_addresses]

    for address in list_of_addresses:
        city_name = get_city_name_from_address(address)
        if city_name not in cities:
            city_data = get_city(city_name)
            cities[city_name] = {}
            cities[city_name]['city_data'] = city_data
            cities[city_name]['intersecting_streets'] = None
            cities[city_name]['intersections'] = set()
            if city_data is None:
                cities[city_name]['intersecting_streets'] = None
            else:
                cities[city_name]['intersecting_streets'] = get_intersecting_streets(city_data)

        if cities[city_name]['intersecting_streets'] is None:
            continue

        intersection_candidates = set(copy.deepcopy(cities[city_name]['intersecting_streets']))
        for street_name in [s.strip() for s in (address.split(',')[0]).split('and')]:
            intersection_candidates = get_intersections_for_a_street(street_name, intersection_candidates)

        cities[city_name]['intersections'] = cities[city_name]['intersections'] | intersection_candidates

    result = []
    for city_name in cities:
        for x_name in cities[city_name]['intersections']:
            result.append(get_intersection(x_name, cities[city_name]['city_data'], size=size, crop_radius=crop_radius))

    return result


def get_crosswalks(intersection_data):
    """
    Return a list of crosswalks
    :param intersection_data: dictionary
    :return: list of dictionaries
    """
    return intersection_data['crosswalks']


def get_approaches(intersection_data):
    """
    Return a list of approaches for an intersection.  
    An approach is a dictionary defining a lane approaching an intersection.

    'name' - street name
    'approach_id' - approach number (zero based) for a given intersection 
    'bearing' - compass bearing in degrees,
    'compass' - compass point: 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'
    'lane_id' - a string identifying a lane, for example: '1', '2', '1R', '1L', '2L'.  Numbers are from right to left
    'direction' - direction: 'to_intersection', 'from_intersection', 'undefined'
    'cycleway' - presence of a bicycle lane
    'cycleway:left' - location of a bicycle lane
    'cycleway:right' - location of a bicycle lane
    'sidewalk' - presence of a sidewalk if applicable
    'hov' - presence of HOV lanes
    'maxspeed' - speed limit if applicable
    'width' - list of lane widths in meters
    'num_of_trunk_lanes' - number of main lanes
    'num_of_right_lanes' - number of right turn lanes
    'num_of_left_lanes' - number of left turn lanes
    'crosswalk_width' - assumed width of a crosswalk in meters (crosswalk presence is not recorded in the input data)

    :param intersection_data: dictionary
    :return: list of dictionaries
    """
    return [m for m in intersection_data['merged_lanes'] if m['direction'] == 'to_intersection']


def get_exits(intersection_data):
    """
    Return a list of exits for an intersection.  
    An approach is a dictionary defining a lane approaching an intersection.

    'name' - street name
    'approach_id' - approach number (zero based) for a given intersection 
    'bearing' - compass bearing in degrees,
    'compass' - compass point: 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'
    'lane_id' - a string identifying a lane, for example: '1', '2', '1R', '1L', '2L'.  Numbers are from right to left
    'direction' - direction: 'to_intersection', 'from_intersection', 'undefined'
    'cycleway' - presence of a bicycle lane
    'cycleway:left' - location of a bicycle lane
    'cycleway:right' - location of a bicycle lane
    'sidewalk' - presence of a sidewalk if applicable
    'hov' - presence of HOV lanes
    'maxspeed' - speed limit if applicable
    'width' - list of lane widths in meters
    'num_of_trunk_lanes' - number of main lanes
    'num_of_right_lanes' - number of right turn lanes
    'num_of_left_lanes' - number of left turn lanes
    'crosswalk_width' - assumed width of a crosswalk in meters (crosswalk presence is not recorded in the input data)

    :param intersection_data: dictionary
    :return: list of dictionaries
    """
    return [m for m in intersection_data['merged_lanes'] if m['direction'] == 'from_intersection']


def get_guideway_by_approach_id(intersection_data, approach_id):
    """
    Get guideway by approach id.
    :param intersection_data: dictionary
    :param approach_id: integer
    :return: list of guideways
    """

    return [g for g in get_guideways(intersection_data, guideway_type='all') if g ['origin_lane']['id'] == approach_id]


def get_guideway_by_exit_id(intersection_data, exit_id):
    """
    Get guideway by exit id.
    :param intersection_data: dictionary
    :param exit_id: integer
    :return: list of guideways
    """
    return [g for g in get_guideways(intersection_data, guideway_type='all') if g['destination_lane']['id'] == exit_id]


def get_intersection_image(intersection_data, alpha=1.0):
    """
    Get an image of intersection lanes in PNG format
    :param intersection_data: dictionary
    :return: matplotlib.figure.Figure
    """

    fig, ax = plot_lanes(intersection_data['merged_lanes'],
                         fig=None, ax=None,
                         cropped_intersection=intersection_data['cropped_intersection'],
                         fig_height=15,
                         fig_width=15,
                         axis_off=False,
                         edge_linewidth=1,
                         margin=0.02,
                         bgcolor='#CCFFE5',
                         edge_color='w',  #'#FF9933',
                         alpha=alpha
                         )

    fig, ax = plot_lanes(intersection_data['merged_tracks'],
                         fig=fig, ax=ax,
                         cropped_intersection=None,
                         fig_height=15,
                         fig_width=15,
                         axis_off=False,
                         edge_linewidth=1,
                         margin=0.02,
                         fcolor='#C0C0C0',
                         edge_color='#000000',
                         alpha=alpha,
                         linestyle='solid'
                         )

    fig, ax = plot_lanes(intersection_data['merged_cycleways'],
                         fig=fig, ax=ax,
                         cropped_intersection=None,
                         fig_height=15,
                         fig_width=15,
                         axis_off=False,
                         edge_linewidth=1,
                         margin=0.02,
                         fcolor='#00FF00',
                         edge_color='#00FF00',
                         alpha=alpha,
                         linestyle='solid'
                         )
    return fig


def get_guideways(intersection_data, guideway_type='all'):
    """
    Get a list of guideways for the intersection by the specified type.

    Valid type options:
    all
    all vehicle
    vehicle right
    vehicle left
    vehicle through
    all bicycle
    bicycle right
    bicycle left
    bicycle through
    all rail
    rail
    
    :param intersection_data: dictionary
    :param guideway_type: string
    :return: list of dictionaries
    """
    guideways = []
    if 'vehicle' in guideway_type and 'left' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        guideways.extend(get_left_turn_guideways(intersection_data['merged_lanes'],
                                                 intersection_data['nodes'],
                                                 angle_delta=2.0
                                                 )
                         )
    if 'vehicle' in guideway_type and 'right' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        guideways.extend(get_right_turn_guideways(intersection_data['merged_lanes']))

    if 'vehicle' in guideway_type and 'through' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        guideways.extend(get_through_guideways(intersection_data['merged_lanes']
                                               + intersection_data['merged_tracks']))

    if 'rail' in guideway_type:
        guideways.extend(get_through_guideways(intersection_data['merged_tracks']))

    if ('bicycle' in guideway_type and 'left' in guideway_type) \
            or (guideway_type == 'all bicycle') \
            or (guideway_type == 'all'):
        guideways.extend(get_left_turn_guideways(intersection_data['merged_cycleways'],
                                                 intersection_data['nodes'],
                                                 angle_delta=2.0
                                                 )
                         )

    if ('bicycle' in guideway_type and 'right' in guideway_type) \
            or (guideway_type == 'all bicycle') \
            or (guideway_type == 'all'):
        guideways.extend(get_right_turn_guideways(intersection_data['merged_cycleways']))

    if ('bicycle' in guideway_type and 'through' in guideway_type) \
            or (guideway_type == 'all bicycle') \
            or (guideway_type == 'all'):
        guideways.extend(get_through_guideways(intersection_data['merged_cycleways']))

    return set_guideway_ids(guideways)


def get_meta_data(data):
    """
    Get meta data from a guideway, approach, exit or lane.  
    If the parameter is a guideway, the function returns meta data for the origin, destination and link (if applicable).
    For all other parameter types, the function returns a meta data dictionary.

    Sample meta data:
    {'bicycle_lane_on_the_left': 'no',
    'bicycle_lane_on_the_right': 'yes',
    'compass': 'NW',
    'id': 9,
    'identification': u'North 1st Street from_intersection',
    'lane_type': '',
    'number_of_crosswalks': 1,
    'number_of_left-turning_lanes': 0,
    'number_of_right-turning_lanes': 0,
    'public_transit_stop': None,
    'rail_track': 'no',
    'right_turn_dedicated_link': 'no',
    'timestamp': '2018-04-04 11:08:04.675000',
    'total_number_of_vehicle_lanes': 2,
    'traffic_signals': 'yes'}

    :param data: dictionary
    :return: dictionary
    """
    if 'origin_lane' in data and 'destination_lane' in data:
        meta_data = {
            'origin_lane': data['origin_lane']['meta_data'],
            'destination_lane': data['destination_lane']['meta_data']
        }
        if 'link_lane' in data:
            meta_data['link_lane'] = data['link_lane']['meta_data']
        return meta_data
    else:
        if 'meta_data' in data:
            return data['meta_data']
        else:
            return None


def get_guideway_image(guideways, intersection_data, alpha=1.0):
    """
    Get an image of guideways in PNG format
    :param guideways: list of dictionaries
    :param intersection_data: dictionary
    :return: matplotlib.figure.Figure
    """
    fig, ax = plot_lanes(intersection_data['merged_lanes'],
                         fig=None, ax=None,
                         cropped_intersection=intersection_data['cropped_intersection'],
                         fig_height=15,
                         fig_width=15,
                         axis_off=False,
                         edge_linewidth=1,
                         margin=0.02,
                         bgcolor='#CCFFE5',
                         edge_color='#FF9933',
                         alpha=alpha
                         )

    fig, ax = plot_lanes(intersection_data['merged_tracks'],
                         fig=fig, ax=ax,
                         cropped_intersection=None,
                         fig_height=15,
                         fig_width=15,
                         axis_off=False,
                         edge_linewidth=1,
                         margin=0.02,
                         fcolor='#C0C0C0',
                         edge_color='#000000',
                         alpha=alpha,
                         linestyle='solid'
                         )

    guideway_fig, guideway_ax = plot_guideways(guideways, fig=fig, ax=ax, alpha=alpha, fc='#FFFF66', ec='b')
    return guideway_fig
