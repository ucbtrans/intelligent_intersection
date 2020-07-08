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
    get_through_guideways, get_bicycle_left_turn_guideways, get_u_turn_guideways, relative_cut
from city import get_city_name_from_address
from node import get_nodes_dict
from data import get_data_from_file, get_city_from_osm
from conflict import get_conflict_zones_per_guideway, plot_conflict_zones, plot_conflict_zone
from blind import get_blind_zone_data, plot_sector, normalized_to_geo
from correction import add_missing_highway_tag
from log import get_logger

logger = get_logger()


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
        'nodes': get_nodes_dict(city_paths_nodes, nodes_dict={}),
        'relations': [p for p in city_paths_nodes[0]['elements'] if p['type'] == 'relation']
    }

    add_missing_highway_tag(city_data['paths'], get_streets(city_data))

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
        'nodes': get_nodes_dict(selection, nodes_dict={}),
        'relations': [p for p in selection[0]['elements'] if p['type'] == 'relation']
    }

    add_missing_highway_tag(selection_data['paths'], get_streets(selection_data))

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
    if city_data is None:
        return set([])

    return set([p['tags']['name'] for p in city_data['paths']
                if 'tags' in p and 'name' in p['tags'] and 'highway' in p['tags']
                ]
               )


def get_intersecting_streets(city_data):
    """
    Get a list of crossing streets.  Each element is a tuple of two or more street names.
    :param city_data: dictionary
    :return: list of tuples
    """
    if city_data is None:
        return []

    intersecting_streets = set()
    all_streets = get_streets(city_data)

    for node_id in city_data['nodes']:
        if 'street_name' in city_data['nodes'][node_id] and len(
                city_data['nodes'][node_id]['street_name']) > 1:
            valid_street_name = True
            for street_name in city_data['nodes'][node_id]['street_name']:
                if street_name not in all_streets:
                    valid_street_name = False
                    break
            if valid_street_name:
                intersecting_streets.add(
                    tuple(sorted(list(city_data['nodes'][node_id]['street_name']))))

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
    if city_data is None:
        logger.error('City data is None')
        return None
    try:
        intersection_data = get_intersection_data(street_tuple, city_data, size=size,
                                                  crop_radius=crop_radius)
    except Exception as e:
        logger.exception('Exception %r, %s, %r' % (street_tuple, city_data['name'], e))
        return None
    return intersection_data


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
            if x_tuple is None:
                continue
            intersection_data = get_intersection(x_tuple, cities[city_name], size=size,
                                                 crop_radius=crop_radius)
            if intersection_data is not None:
                result.append(intersection_data)

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


def get_street_data_list(intersection_data):
    """
    Get a list of street data for the intersection. 
    The street data includes street name, id and street borders from left to right.
    :param intersection_data: intersection dictionary
    :return: list of street data dictionaries
    """
    if intersection_data is None:
        return []
    return intersection_data['street_data']


def get_street_image(street_data_list, intersection_data, fc='#FFCCCC', ec='b', alpha=1.0):
    """
    Get an image of streets for the intersection
    :param street_data_list: list of street data dictionaries
    :param intersection_data: intersection dictionary
    :param alpha: transparency between 0 and 1
    :return: image
    """
    return get_guideway_image(street_data_list, intersection_data, fc=fc, ec=ec, alpha=alpha)


def get_crosswalks(intersection_data):
    """
    Return a list of crosswalks
    :param intersection_data: dictionary
    :return: list of dictionaries
    """
    if intersection_data is None:
        return []
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

    return [g for g in get_guideways(intersection_data, guideway_type='all') if
            g['origin_lane']['id'] == approach_id]


def get_guideway_by_exit_id(intersection_data, exit_id):
    """
    Get guideway by exit id.
    :param intersection_data: dictionary
    :param exit_id: integer
    :return: list of guideways
    """
    return [g for g in get_guideways(intersection_data, guideway_type='all') if
            g['destination_lane']['id'] == exit_id]


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
    
    Guideway is dictionary with the following keys: 
     'direction',
     'origin_lane',
     'destination_lane',
     'right_border',
     'left_border',
     'median',
     'id',
     'type',
     'length'

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
        logger.debug('Starting %s vehicle guideways' % guideway_type)
        guideways.extend(get_left_turn_guideways(intersection_data['merged_lanes'],
                                                 intersection_data['nodes'],
                                                 )
                         )
    if 'vehicle' in guideway_type and 'right' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        logger.debug('Starting %s  vehicle guideways' % guideway_type)
        guideways.extend(get_right_turn_guideways(intersection_data['merged_lanes']))

    if 'vehicle' in guideway_type and 'through' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        logger.debug('Starting %s vehicle guideways' % guideway_type)
        guideways.extend(get_through_guideways(intersection_data['merged_lanes']))

    if 'vehicle' in guideway_type and 'u-turn' in guideway_type \
            or (guideway_type == 'all vehicle') \
            or (guideway_type == 'all'):
        logger.debug('Starting %s vehicle guideways' % guideway_type)
        guideways.extend(get_u_turn_guideways(intersection_data['merged_lanes'], intersection_data))

    if 'rail' in guideway_type or (guideway_type == 'all'):
        logger.debug('Starting %s rail guideways' % guideway_type)
        guideways.extend(get_through_guideways(intersection_data['merged_tracks']))

    if ('bicycle' in guideway_type and 'left' in guideway_type) \
            or (guideway_type == 'all bicycle') \
            or (guideway_type == 'all'):
        logger.debug('Starting %s - adding left bicycle guideways' % guideway_type)
        guideways.extend(get_bicycle_left_turn_guideways(intersection_data['merged_cycleways'],
                                                         intersection_data['nodes']
                                                         )
                         )

    if ('bicycle' in guideway_type and 'right' in guideway_type) \
            or (guideway_type == 'all bicycle') \
            or (guideway_type == 'all'):
        logger.debug('Starting %s - adding right bicycle guideways' % guideway_type)
        guideways.extend(get_right_turn_guideways(intersection_data['merged_cycleways']))

    if ('bicycle' in guideway_type and 'through' in guideway_type) \
            or (guideway_type == 'all bicycle') \
            or (guideway_type == 'all'):
        logger.debug('Starting %s - adding through bicycle guideways' % guideway_type)
        guideways.extend(get_through_guideways(intersection_data['merged_cycleways']))

    return guideways


def get_reduced_guideway(guideway_data, relative_distance, starting_point_for_cut="b"):
    """
    Reduce guideway by relative distance from either end.  The distance is in the range [0;1].
    The starting point can be either 'b' or 'e';  The guideway left and right borders and median will truncated.
    For example, if relative_distance = 0.3 and starting_point_for_cut="b", 
    then the function returns 30% of the original length starting from the beginning of the guideway.
    If relative_distance = 0.3 and starting_point_for_cut="e", 
    then the function returns 30% of the original length adjacent to the end of the guideway.
    The length of the reduced guideway is updated to reflect the new actual length 
    while the lengths of the origin and destination lanes are preserved in the lane meta data.
    :param guideway_data: guideway dictionary
    :param relative_distance: relative length
    :param starting_point_for_cut: string, either 'b' or 'e'
    :return: guideway dictionary with reduced borders and median
    """
    return relative_cut(guideway_data, relative_distance, starting_point_for_cut)


def get_length(data):
    """
    Get length of a guideway, approach, exit or lane. 
    The length is calculated as a sum of distances between sequential nodes of the median.
    Generally the length of a guideway is not equal to the origin lane + destination lane lengths 
    because the guideway includes a curved turn from the origin lane to the destination one.
    For reduced guideways the length is reduced and reflects the actual length of the reduced guideway.

    :param data: dictionary of a guideway, approach, exit or lane
    :return: float in meters
    """
    if 'length' in data:
        return data['length']
    elif 'meta_data' in data and 'length' in data['meta_data']:
        return data['meta_data']['length']
    else:
        return None


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

        if 'length' in data:
            meta_data['length'] = data['length']

        return meta_data
    else:
        if 'meta_data' in data:
            return data['meta_data']
        else:
            return None


def get_guideway_image(guideways, intersection_data, fc='#FFFF66', ec='b', alpha=1.0):
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

    guideway_fig, guideway_ax = plot_guideways(guideways, fig=fig, ax=ax, alpha=alpha, fc=fc, ec=ec)
    return guideway_fig


def get_conflict_zones(guideway_data, all_guideways=None, intersection_data=None):
    """
    Get a list of conflict zones for a guideway
    :param guideway_data: guideway data dictionary
    :param all_guideways: list of all guideway data dictionaries
    :param intersection_data: intersection data dictionary
    :return: list of conflict zone dictionaries
    """

    polygons_dict = {}
    if all_guideways is None:
        if intersection_data is None:
            return []
        all_guideways = get_guideways(intersection_data, guideway_type='all') + get_crosswalks(
            intersection_data)

    return get_conflict_zones_per_guideway(guideway_data, all_guideways, polygons_dict)


def get_all_conflict_zones(intersection_data, all_guideways=[]):
    """
    Get a list of conflict zones for all guideways
    :param intersection_data: intersection data dictionary
    :param all_guideways: list of all guideway dictionaries
    :return: list of conflict zone dictionaries
    """

    all_conflict_zones = []

    if not all_guideways:
        all_guideways = get_guideways(intersection_data, guideway_type='all') + get_crosswalks(
            intersection_data)
    polygons_dict = {}
    for guideway_data in all_guideways:
        all_conflict_zones.extend(
            get_conflict_zones_per_guideway(guideway_data, all_guideways, polygons_dict))

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

    conflict_zone_fig, conflict_zone_ax = plot_conflict_zone(conflict_zone, fig=fig, ax=ax,
                                                             alpha=alpha)

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

    conflict_zone_fig, conflict_zone_ax = plot_conflict_zones(conflict_zones, fig=fig, ax=ax,
                                                              alpha=alpha)

    return conflict_zone_fig


def get_geo_coordinates(point_of_view, guideway_data, conflict_zone=None):
    """
    Convert normalized coordinates (between 0 and 1) to lon and lat.
    point_of_view[0] is relative distance from the beginning of the median to the intersection with the conflict zone.
    The first parameter of the point_of_view tuple is a distance along the median of the guideway.
    0 is a point at the beginning of the guideway.
    1 is a point at the intersection of the guideway median and the conflict zone.
    If the conflict zone is None (not specified), then 1 means the end of the guideway.    
    point_of_view[1] is position within the width of the guideway, 
    where 0.5 is on the median, 0 on the left border and 1 on the right border.
    :param point_of_view: a tuple of floats between 0 and 1
    :param conflict_zone: conflict zone dictionary
    :param guideway_data: guideway dictionary
    :return: a tuple of lon and lat
    """

    return normalized_to_geo(point_of_view, guideway_data, conflict_zone=conflict_zone)


def get_blind_zone(point_of_view, current_guideway, conflict_zone, blocking_guideways,
                   all_guideways):
    """
    Get a blind zone
    :param point_of_view: normalized coordinates along the current guideway: (x,y), where x and y within [0.0,1.0]
    :param current_guideway: guideway dictionary
    :param conflict_zone: conflict zone dictionary.  It must belong to the current guideway
    :param blocking_guideways: list of guideway dictionaries representing guideways creating blind zones
    :param all_guideways: list of all guideway dictionaries in the intersection
    :return: blind zone dictionary
    """
    if point_of_view is None or current_guideway is None or conflict_zone is None \
            or blocking_guideways is None or all_guideways is None:
        return None

    try:
        for guideway_data in all_guideways:
            if 'reduced_left_border' not in guideway_data:
                get_conflict_zones_per_guideway(guideway_data, all_guideways, {})
        blind_zone_data = get_blind_zone_data(point_of_view,
                                              current_guideway,
                                              conflict_zone,
                                              blocking_guideways,
                                              all_guideways
                                              )
    except Exception as e:
        logger.error('Blind zone exception: point %r, guideway %d, conflict zone %r'
                     % (point_of_view, current_guideway['id'], conflict_zone['id']))
        logger.exception('Exception: %r' % e)
        return None

    return blind_zone_data


def get_blind_zone_image(blind_zone, current_guideway, intersection_data, blocks=None, alpha=1.0,
                         fc='r', ec='r'):
    """
    Get an image of a list of conflict zones in PNG format
    :param blind_zone: blind zone dictionary
    :param current_guideway: guideway dictionary
    :param intersection_data: intersection dictionary
    :param fc: foreground color
    :param ec: edge color
    :param alpha: transparency: between 0.0 amd 1.0
    :param blocks: reserved for future use
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

    if blind_zone is None:
        return fig

    blind_zone_fig, blind_zone_ax = plot_sector(current_guideway=current_guideway,
                                                x_data=intersection_data,
                                                blocks=blocks,
                                                point_of_view=blind_zone['geo_point'],
                                                conflict_zone=blind_zone['conflict_zone'],
                                                fig=fig,
                                                ax=ax,
                                                blind_zone=blind_zone['polygon'],
                                                fc=fc,
                                                ec=ec
                                                )

    return blind_zone_fig
