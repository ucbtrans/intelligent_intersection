#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides top level API routines
#
#######################################################################


import copy
import osmnx as ox
from intersection import get_nodes_dict, get_intersection_data, plot_lanes
from street import insert_street_names, get_intersections_for_a_street
from lane import get_lanes, merge_lanes, shorten_lanes
from guideway import get_left_turn_guideways, get_right_turn_guideways, plot_guideways
from city import get_city_name_from_address


def get_city(city_name):
    """
    Get street structure of a city
    :param city_name: city name like 'Campbell, California, USA'
    :return: a tuple of list of paths and a nodes dictionary
    """
    try:
        city_boundaries = ox.gdf_from_place(city_name)
        city_paths_nodes = ox.osm_net_download(city_boundaries['geometry'].unary_union, network_type="drive")
    except KeyError:
        return None
    nodes_dict = get_nodes_dict(city_paths_nodes)
    paths = [p for p in city_paths_nodes[0]['elements'] if p['type'] != 'node']
    city = {
        'name': city_name,
        'paths': paths,
        'nodes': nodes_dict
    }
    return insert_street_names(city)


def get_streets(city):
    """
    Get set of streets from a city structure
    :param city: dictionary
    :return: return a set of street names
    """

    return set([p['tags']['name'] for p in city['paths'] if 'name' in p['tags']])


def get_intersecting_streets(city):
    """
    Get a list of intersecting street.  Each element is a tuple of two or more street names.
    :param city: dictionary
    :return: list of tuples
    """
    intersecting_streets = set()

    for node in city['nodes']:
        if 'street_name' in city['nodes'][node] and len(city['nodes'][node]['street_name']) > 1:
            intersecting_streets.add(tuple(sorted(list(city['nodes'][node]['street_name']))))

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


def get_intersection(street_tuple, city, size=500.0, crop_radius=150.0):
    """
    Get a dictionary with all data related to an intersection.
    :param street_tuple: tuple of strings
    :param city: dictionary
    :param size: initial size of the surrounding area in meters
    :param crop_radius: the data will be cropped to the specified radius in meters
    :return: dictionary
    """
    cleaned_intersection_paths, cropped_intersection = get_intersection_data(city['paths'],
                                                                             city['nodes'],
                                                                             street_tuple,
                                                                             size=size,
                                                                             crop_radius=crop_radius
                                                                             )

    lanes = get_lanes(cleaned_intersection_paths, city['nodes'])
    merged_lanes = merge_lanes(lanes)
    shorten_lanes(merged_lanes)

    intersection_data = {
        'city': city['name'],
        'streets': street_tuple,
        'lanes': lanes,
        'merged_lanes': merged_lanes,
        'cropped_intersection': cropped_intersection
    }

    return intersection_data


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
            city = get_city(city_name)
            cities[city_name] = {}
            cities[city_name]['city_data'] = city
            cities[city_name]['intersecting_streets'] = None
            cities[city_name]['intersections'] = set()
            if city is None:
                cities[city_name]['intersecting_streets'] = None
            else:
                cities[city_name]['intersecting_streets'] = get_intersecting_streets(city)

        if cities[city_name]['intersecting_streets'] is None:
            continue

        intersection_candidates = set(copy.deepcopy(cities[city_name]['intersecting_streets']))
        for street in [s.strip() for s in (address.split(',')[0]).split('and')]:
            intersection_candidates = get_intersections_for_a_street(street, intersection_candidates)

        cities[city_name]['intersections'] = cities[city_name]['intersections'] | intersection_candidates

    result = []
    for city_name in cities:
        for x_name in cities[city_name]['intersections']:
            result.append(get_intersection(x_name, cities[city_name]['city_data'], size=size, crop_radius=crop_radius))

    return result


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


def get_intersection_image(intersection_data):
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
                         edge_color='#FF9933',
                         alpha=1.0
                         )

    return fig


def get_guideways(intersection_data, guideway_type='all'):
    """
    Get a list of guideways for the intersection.  Presently only left and right turns have been implemented
    :param intersection_data: dictionary
    :param guideway_type: string
    :return: list of dictionaries
    """
    guideways = []
    if guideway_type == 'left' or 'all':
        guideways.extend(get_left_turn_guideways(intersection_data['merged_lanes'], angle_delta=2.0))
    if guideway_type == 'right' or 'all':
        guideways.extend(get_right_turn_guideways(intersection_data['merged_lanes']))

    return guideways


def get_guideway_image(guideways, intersection_data):
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
                         alpha=1.0
                         )

    guideway_fig, guideway_ax = plot_guideways(guideways, fig=fig, ax=ax, alpha=0.9, fc='#FFFF66', ec='b')
    return guideway_fig
