#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides top level API routines
#
#######################################################################


from intersection import get_intersection_data, plot_lanes
from street import insert_street_names
from guideway import get_left_turn_guideways, get_right_turn_guideways, plot_guideways, \
    get_through_guideways, set_guideway_ids, get_bicycle_left_turn_guideways, get_u_turn_guideways
from city import get_city_name_from_address
from node import get_nodes_dict
from data import get_data_from_file, get_city_from_osm
from conflict import get_conflict_zones_per_guideway, plot_conflict_zones, plot_conflict_zone


def get_city(city_name):
    """
    Get city data as a dictionary.
    :param city_name: city name like 'Campbell, California, USA'
    :return: city data dictionary
    """

    city_paths_nodes = get_city_from_osm(city_name)

    if city_paths_nodes is None:
        return None

    city_data = {
        'name': city_name,
        'raw_data': None,
        'from_file': 'no',
        'paths': [p for p in city_paths_nodes[0]['elements'] if p['type'] == 'way'],
        'nodes': get_nodes_dict(city_paths_nodes),
        'relations': [p for p in city_paths_nodes[0]['elements'] if p['type'] == 'relation']
    }
    return insert_street_names(city_data)


def get_selection(file_name):
    """
    Get selection from an XML file.  Returns a dictionary with the data from the file 
    or None if unable to read/parse the file.
    :param file_name: string
    :return: selection data dictionary
    """

    selection = get_data_from_file(file_name)
    if selection is None:
        return None

    selection_data = {
        'name': file_name,
        'raw_data': selection,
        'from_file': 'yes',
        'paths': [p for p in selection[0]['elements'] if p['type'] == 'way'],
        'nodes': get_nodes_dict(selection),
        'relations': [p for p in selection[0]['elements'] if p['type'] == 'relation']
    }
    return insert_street_names(selection_data)


def get_data(city_name=None, file_name=None):
    """
    Get data either from OSM by city name or from an XML file by file name.
    If the city name is not None, than data will be downloaded from OSM online.
    If the file name is not None, the data will be loaded from the file.
    If both are not None, the file will be ignored and the city name parameter prevails.
    Returns a dictionary with the desired data or None if not found.
    :param city_name: city name like 'Campbell, California, USA'
    :param file_name: string
    :return: selection data dictionary
    """
    if city_name is not None:
        return get_city(city_name)
    elif file_name is not None:
        return get_selection(file_name)
    else:
        return None


def get_streets(city_data):
    """
    Get set of streets from a city structure
    :param city_data: dictionary
    :return: return a set of street names
    """

    return set([p['tags']['name'] for p in city_data['paths'] if 'name' in p['tags'] and 'highway' in p['tags']])


def get_intersecting_streets(city_data):
    """
    Get a list of crossing streets.  Each element is a tuple of two or more street names.
    :param city_data: dictionary
    :return: list of tuples
    """
    intersecting_streets = set()
    all_streets = get_streets(city_data)

    for node_id in city_data['nodes']:
        if 'street_name' in city_data['nodes'][node_id] and len(city_data['nodes'][node_id]['street_name']) > 1:
            valid_street_name = True
            for street_name in city_data['nodes'][node_id]['street_name']:
                if street_name not in all_streets:
                    valid_street_name = False
                    break
            if valid_street_name:
                intersecting_streets.add(tuple(sorted(list(city_data['nodes'][node_id]['street_name']))))

    multiples = [x for x in intersecting_streets if len(x) > 2]
    duplicates = set()
    for x in intersecting_streets:
        if len(x) > 2:
            continue

        for y in multiples:
            if x[0] in y and x[1] in y:
                duplicates.add(x)

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
    You can use a single address as a string instead of a list.  The return will be a list in any case.
    Street names must separated by and, followed by coma and city, state,
    like 'Solano and Pierce, Albany, California'.  
    An address like 'Dar and K, Albany, California' returns more than one intersection:
    ('Dartmouth Street', 'Kains Avenue'),
    ('Dartmouth Street', 'Key Route Boulevard')
    Please spell out California instead of CA, because CA can be interpreted as Canada
    :param list_of_addresses: list of strings or a string
    :param size: float in meters
    :param crop_radius: float in meters
    :return: list of intersections as dictionaries
    """

    cities = {}
    result = []
    if not isinstance(list_of_addresses, list):
        list_of_addresses = [list_of_addresses]

    for address in list_of_addresses:
        city_name = get_city_name_from_address(address)
        if city_name not in cities:
            cities[city_name] = get_city(city_name)

        for x_tuple in get_intersection_tuples_by_address(cities[city_name], address):
            result.append(get_intersection(x_tuple, cities[city_name], size=size, crop_radius=crop_radius))

    return result


def get_intersection_tuples_by_address(city_data, address):
    """
    Returns a set of intersection tuples for an address or a list of addresses.
    The address(es) must be in the same city. The result can be empty if no match.
    Street names must separated by and, followed by coma and city, state,
    like 'Solano and Pierce, Albany, California'.  
    An address like 'Dar and K, Albany, California' returns more than one intersection:
    ('Dartmouth Street', 'Kains Avenue'),
    ('Dartmouth Street', 'Key Route Boulevard')
    Please spell out California, because CA will be taken as Canada
    :param city_data: dictionary
    :param address: string or list of strings
    :return: set of street name tuples
    """

    result = set()
    if city_data is None:
        return result

    if not isinstance(address, list):
        list_of_addresses = [address]
    else:
        list_of_addresses = address

    x_streets = get_intersecting_streets(city_data)

    for a in list_of_addresses:
        street_names = [s.strip() for s in (a.split(',')[0]).split('and')]
        for x in x_streets:
            flag = True
            x_name = ' '.join(x)
            for street_name in street_names:
                if street_name in x_name:
                    continue
                else:
                    flag = False
                    break
            if flag:
                result.add(x)
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

    return [g for g in get_guideways(intersection_data, guideway_type='all') if g['origin_lane']['id'] == approach_id]


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
    :param alpha: transparency: between 0.0 amd 1.0
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
                         edge_color='w',  # '#FF9933',o
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

    if intersection_data is None:
        return []

    guideway_type = guideway_type.lower()
    guideways = []
    if 'vehicle' in guideway_type and 'left' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        guideways.extend(get_left_turn_guideways(intersection_data['merged_lanes'],
                                                 intersection_data['nodes'],
                                                 )
                         )
    if 'vehicle' in guideway_type and 'right' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        guideways.extend(get_right_turn_guideways(intersection_data['merged_lanes']))

    if 'vehicle' in guideway_type and 'through' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        guideways.extend(get_through_guideways(intersection_data['merged_lanes']))

    if 'vehicle' in guideway_type and 'u-turn' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        guideways.extend(get_u_turn_guideways(intersection_data['merged_lanes'], intersection_data))

    if 'rail' in guideway_type or (guideway_type == 'all'):
        guideways.extend(get_through_guideways(intersection_data['merged_tracks']))

    if ('bicycle' in guideway_type and 'left' in guideway_type) \
            or (guideway_type == 'all bicycle') \
            or (guideway_type == 'all'):
        guideways.extend(get_bicycle_left_turn_guideways(intersection_data['merged_cycleways'],
                                                         intersection_data['nodes']
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

    return guideways


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
    :param alpha: transparency: between 0.0 amd 1.0
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


def get_conflict_zones(guideway_data, all_guideways=None, intersection_data=None):
    """
    Get a list of conflict zones for a guideway
    :param guideway_data: guideway data dictionary
    :param all_guideways: list of all guideway data dictionaries
    :param intersection_data: intersection data dictionary
    :return: list of conflict zone dictionaries
    """

    if all_guideways is None:
        if intersection_data is None:
            return []
        all_guideways = get_guideways(intersection_data, guideway_type='all') + get_crosswalks(intersection_data)

    return get_conflict_zones_per_guideway(guideway_data, all_guideways)


def get_all_conflict_zones(intersection_data):
    """
    Get a list of conflict zones for all guideways
    :param intersection_data: intersection data dictionary
    :return: list of conflict zone dictionaries
    """

    all_conflict_zones = []
    all_guideways = get_guideways(intersection_data, guideway_type='all') + get_crosswalks(intersection_data)
    polygons_dict = {}
    for guideway_data in all_guideways:
        all_conflict_zones.extend(get_conflict_zones_per_guideway(guideway_data, all_guideways, polygons_dict))

    return all_conflict_zones


def get_single_conflict_zone_image(conflict_zone, intersection_data, alpha=1.0):
    """
    Get an image of a conflict zone in PNG format
    :param conflict_zone: dictionary
    :param intersection_data: dictionary
    :param alpha: transparency: between 0.0 amd 1.0
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

    conflict_zone_fig, conflict_zone_ax = plot_conflict_zone(conflict_zone, fig=fig, ax=ax, alpha=alpha)

    return conflict_zone_fig


def get_conflict_zone_image(conflict_zones, intersection_data, alpha=1.0):
    """
    Get an image of a list of conflict zones in PNG format
    :param conflict_zones: list of dictionaries
    :param intersection_data: dictionary
    :param alpha: transparency: between 0.0 amd 1.0
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

    conflict_zone_fig, conflict_zone_ax = plot_conflict_zones(conflict_zones, fig=fig, ax=ax, alpha=alpha)

    return conflict_zone_fig
