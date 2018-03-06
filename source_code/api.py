#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides top level API routines
#
#######################################################################


import osmnx as ox
from intersection import get_nodes_dict, get_intersection_data, plot_lanes
from street import insert_street_names
from lane import get_lanes, merge_lanes, shorten_lanes
from guideway import get_left_turn_guideways, get_right_turn_guideways, plot_guideways


def get_city(city_name):
    """
    Get street structure of a city
    :param city_name: city name like 'Campbell, California, USA'
    :return: a tuple of list of paths and a nodes dictionary
    """
    city_boundaries = ox.gdf_from_place(city_name)
    city_paths_nodes = ox.osm_net_download(city_boundaries['geometry'].unary_union, network_type="drive")
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
