#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module creates intersection data structure
#
#######################################################################

import osmnx as ox
from lane import get_lanes, merge_lanes, shorten_lanes, get_bicycle_lanes
from meta import set_meta_data
from matplotlib.patches import Polygon
from path import add_borders_to_paths, split_bidirectional_paths, clean_paths, remove_zero_length_paths, set_direction
from node import get_nodes_dict, get_center, get_node_subset, get_intersection_nodes, \
    add_nodes_to_dictionary, get_node_dict_subset_from_list_of_lanes, create_a_node_from_coordinates
from street import select_close_nodes, split_streets, get_list_of_street_data
from railway import split_railways, remove_subways
from footway import get_crosswalks, get_simulated_crosswalks
from correction import manual_correction, correct_paths
from border import border_within_box, get_box, get_border_length, great_circle_vec_check_for_nan
from data import get_box_from_xml, get_box_data
from log import get_logger, dictionary_to_log


logger = get_logger()
track_symbol = {
    'SW': '\\',
    'NE': '\\',
    'N': '-',
    'S': '-',
    'E': '|',
    'W': '|',
    'SE': '/',
    'NW': '/',
}


def get_street_structure(city_name):
    """
    Get street structure of a city
    :param city_name: city name like 'Campbell, California, USA'
    :return: a tuple of list of paths and a nodes dictionary
    """
    city_boundaries = ox.gdf_from_place(city_name)
    city_paths_nodes = ox.osm_net_download(city_boundaries['geometry'].unary_union, network_type="drive")
    nodes_dict = get_nodes_dict(city_paths_nodes)
    paths = [p for p in city_paths_nodes[0]['elements'] if p['type'] != 'node']
    return paths, nodes_dict


def create_intersection(street_tuple, data, size=500.0, crop_radius=150.0):
    """
    Create dictionary of intersection data.  The input data can be either city data or selection data
    :param street_tuple: tuple of strings
    :param data: dictionary
    :param size: float in meters: initial size of osm data
    :param crop_radius: float in meters: the data within the initial size will be cropped to the specified radius
    :return: dictionary
    """
    x_nodes = select_close_nodes(data['nodes'], get_intersection_nodes(data['paths'], street_tuple))

    if x_nodes is None or len(x_nodes) < 1:
        logger.error('Unable to find common nodes referenced in all streets %r' % ', '.join(street_tuple))
        return None

    u, v = get_center(x_nodes, data['nodes'])

    if data['raw_data'] is None:
        north, south, east, west = get_box(u, v, size=size)
    else:
        north, south, east, west = get_box_from_xml(data['raw_data'][0]['bounds'])
    x_data = {
        'city': data['name'],
        'from_file': data['from_file'],
        'streets': street_tuple,
        'center_x': u,
        'center_y': v,
        'north': north,
        'south': south,
        'east': east,
        'west': west,
        'size': size,
        'crop_radius': crop_radius,
        'x_nodes': x_nodes,
        'nodes': {}
        }

    logger.info('Creating Intersection ' + dictionary_to_log(x_data))
    return x_data


def get_max_intersecting_node_distance(x_data):
    """
    Get max distance from the intersection center to intersecting nodes
    :param x_data: intersection dictionary
    :return: float distance
    """
    nodes = [n for n in x_data['nodes'] if len(x_data['nodes'][n]['street_name'] & x_data['streets']) > 1]
    if len(nodes) > 1:
        x0 = x_data['center_x']
        y0 = x_data['center_y']
        dist = [great_circle_vec_check_for_nan(y0, x0, x_data['nodes'][n]['y'], x_data['nodes'][n]['x']) for n in nodes]
        return sum(dist)/len(dist)
    else:
        return 0.0


def get_street_data(x_data, city_data):
    """
    Get a list of paths related to the intersection and a list of data matching the osmnx format.
    :param x_data: dictionary
    :param city_data: dictionary
    :return: a tuple of lists
    """

    nodes_dict = city_data['nodes']
    intersection_jsons = get_box_data(x_data, city_data['raw_data'],
                                      infrastructure='way["highway"]',
                                      network_type='drive'
                                      )

    intersection_paths = [e for e in intersection_jsons[0]['elements'] if e['type'] == 'way']
    add_nodes_to_dictionary([e for e in intersection_jsons[0]['elements'] if e['type'] == 'node'],
                            nodes_dict,
                            paths=intersection_paths
                            )
    manual_correction(intersection_paths)
    split_x_streets = split_streets(intersection_paths, nodes_dict, x_data['streets'])
    oneway_paths = split_bidirectional_paths(split_x_streets, nodes_dict)
    set_direction(oneway_paths, x_data, nodes_dict)
    correct_paths(oneway_paths)
    oneway_paths_with_borders = add_borders_to_paths(oneway_paths, nodes_dict)

    cropped_paths = remove_elements_beyond_radius(oneway_paths_with_borders,
                                                  nodes_dict,
                                                  x_data['center_x'],
                                                  x_data['center_y'],
                                                  x_data['crop_radius']
                                                  )
    cleaned_intersection_paths = clean_paths(cropped_paths, x_data['streets'])
    node_subset = get_node_subset(intersection_jsons, cleaned_intersection_paths, nodes_dict)
    intersection_selection = [{'version': intersection_jsons[0]['version'],
                               'osm3s': intersection_jsons[0]['osm3s'],
                               'generator': intersection_jsons[0]['generator'],
                               'elements': node_subset
                               + cleaned_intersection_paths
                               }
                              ]

    return cleaned_intersection_paths, intersection_selection, intersection_jsons


def get_railway_data(x_data, city_data):
    """
    Get railway data if applicable for the intersection and crop within the radius.
    :param x_data: dictionary
    :param city_data: dictionary 
    :return: list of railway paths 
    """
    nodes_dict = city_data['nodes']
    railway_jsons = get_box_data(x_data, city_data['raw_data'], network_type='all', infrastructure='way["railway"]')

    railway_paths = [e for e in railway_jsons[0]['elements'] if e['type'] == 'way']
    referenced_nodes = {}
    referenced_nodes = get_node_dict_subset_from_list_of_lanes(x_data['merged_lanes'], nodes_dict, referenced_nodes)
    split_railway_paths = split_railways(remove_subways(railway_paths), referenced_nodes)
    add_nodes_to_dictionary([e for e in railway_jsons[0]['elements'] if e['type'] == 'node'],
                            nodes_dict,
                            paths=railway_paths
                            )
    paths_with_borders = add_borders_to_paths(split_railway_paths, nodes_dict, width=2.0)
    cropped_paths = remove_elements_beyond_radius(paths_with_borders,
                                                  nodes_dict,
                                                  x_data['center_x'],
                                                  x_data['center_y'],
                                                  x_data['crop_radius']
                                                  )
    set_direction(cropped_paths, x_data, nodes_dict)
    return cropped_paths


def get_footway_data(x_data, city_data):
    """
    Get footway data if applicable for the intersection and crop within the radius.
    :param x_data: dictionary
    :param city_data: dictionary 
    :return: list of railway paths 
    """
    nodes_dict = city_data['nodes']
    footway_jsons = get_box_data(x_data, city_data['raw_data'], network_type='all')

    footway_paths = [e for e in footway_jsons[0]['elements']
                     if e['type'] == 'way'
                     and 'highway' in e['tags']
                     and 'foot' in e['tags']['highway']
                     ]

    add_nodes_to_dictionary([e for e in footway_jsons[0]['elements'] if e['type'] == 'node'],
                            nodes_dict,
                            paths=footway_paths
                            )
    paths_with_borders = add_borders_to_paths(footway_paths, nodes_dict, width=1.8)
    cropped_paths = remove_elements_beyond_radius(paths_with_borders,
                                                  nodes_dict,
                                                  x_data['center_x'],
                                                  x_data['center_y'],
                                                  x_data['crop_radius']
                                                  )
    set_direction(cropped_paths, x_data, nodes_dict)
    return cropped_paths


def get_public_transit_data(x_data, city_data):
    """
    Get public transit data if applicable for the intersection and crop within the radius.
    :param x_data: dictionary
    :param city_data: dictionary 
    :return: list of railway paths 
    """
    nodes_dict = city_data['nodes']
    public_transit_jsons = get_box_data(x_data,
                                        city_data['raw_data'],
                                        network_type='all',
                                        infrastructure='node["highway"]'
                                        )

    public_transit_nodes = [e for e in public_transit_jsons[0]['elements']
                            if e['type'] == 'node'
                            and 'tags' in e
                            and 'stop' in ' '.join(e['tags'].values())
                            ]

    add_nodes_to_dictionary(public_transit_nodes, nodes_dict, paths=None)

    return public_transit_nodes


def get_intersection_data(street_tuple, city_data, size=500.0, crop_radius=150.0):
    """
    Get a dictionary with all data related to an intersection.
    :param street_tuple: tuple of strings
    :param city_data: dictionary
    :param size: initial size of the surrounding area in meters
    :param crop_radius: the data will be cropped to the specified radius in meters
    :return: dictionary
    """

    if street_tuple is None:
        return None

    intersection_data = create_intersection(street_tuple, city_data, size=size, crop_radius=crop_radius)
    if intersection_data is None:
        logger.error('Invalid intersection %r, %r' % (', '.join(street_tuple), city_data['name']))
        return None

    cleaned_intersection_paths, cropped_intersection, raw_data = get_street_data(intersection_data, city_data)

    lanes = get_lanes(cleaned_intersection_paths, city_data['nodes'])
    merged_lanes = merge_lanes(lanes, city_data['nodes'])

    intersection_data['raw_data'] = raw_data
    intersection_data['lanes'] = lanes
    intersection_data['merged_lanes'] = merged_lanes
    intersection_data['cropped_intersection'] = cropped_intersection
    intersection_data['railway'] = get_railway_data(intersection_data, city_data)
    intersection_data['rail_tracks'] = get_lanes(intersection_data['railway'], city_data['nodes'], width=2.0)
    intersection_data['merged_tracks'] = merge_lanes(intersection_data['rail_tracks'], city_data['nodes'])
    intersection_data['nodes'] = get_node_dict_subset_from_list_of_lanes(intersection_data['rail_tracks'],
                                                                         city_data['nodes'],
                                                                         nodes_subset=intersection_data['nodes']
                                                                         )
    intersection_data['nodes'] = get_node_dict_subset_from_list_of_lanes(intersection_data['lanes'],
                                                                         city_data['nodes'],
                                                                         nodes_subset=intersection_data['nodes']
                                                                         )
    intersection_data['cycleway_lanes'] = get_bicycle_lanes(cleaned_intersection_paths, city_data['nodes'])
    intersection_data['merged_cycleways'] = merge_lanes(intersection_data['cycleway_lanes'], city_data['nodes'])
    intersection_data['footway'] = get_footway_data(intersection_data, city_data)

    intersection_data['street_data'] = get_list_of_street_data(intersection_data['merged_lanes'])
    crosswalks = get_crosswalks(intersection_data['footway'], city_data['nodes'], width=1.8)
    intersection_data['crosswalks'] = crosswalks + get_simulated_crosswalks(intersection_data['street_data'],
                                                                            merged_lanes,
                                                                            crosswalks,
                                                                            width=1.8
                                                                            )
    intersection_data['public_transit_nodes'] = get_public_transit_data(intersection_data, city_data)

    intersection_data['nodes'] = get_node_dict_subset_from_list_of_lanes(intersection_data['cycleway_lanes'],
                                                                         city_data['nodes'],
                                                                         nodes_subset=intersection_data['nodes']
                                                                         )
    intersection_data['nodes'] = get_node_dict_subset_from_list_of_lanes(intersection_data['footway'],
                                                                         city_data['nodes'],
                                                                         nodes_subset=intersection_data['nodes']
                                                                         )

    set_meta_data(intersection_data['merged_lanes']
                  + intersection_data['merged_tracks']
                  + intersection_data['merged_cycleways']
                  + intersection_data['crosswalks'],
                  intersection_data
                  )

    logger.info('Intersection Created')
    return intersection_data


def crop_selection(selection, x0, y0, nodes_dict=None, radius=150.0):
    """
    Crop the selection to a smaller radius
    :param selection: list of intersection data in the osmnx format
    :param x0: float: center coordinate
    :param y0: float: center coordinate
    :param nodes_dict: dictionary
    :param radius: float in meters: cropping radius
    :return: cropped list of intersection data in the osmnx format
    """
    if nodes_dict is None:
        nodes_dict = get_nodes_dict(selection, nodes_dict={})

    cropped_selection = []

    for s in selection:
        s_cropped = {'version': s['version'],
                     'osm3s': s['osm3s'],
                     'generator': s['generator'],
                     'elements': s['elements']
                     }
        s_cropped['element'] = remove_elements_beyond_radius(s_cropped['elements'], nodes_dict, x0, y0, radius)
        cropped_selection.append(s_cropped)

    return cropped_selection


def smart_crop(elements, nodes_dict, x0, y0, radius):

    for e in elements:
        if e['type'] != 'node':
            cropped_node_list = []
            for n in e['nodes']:
                dist = great_circle_vec_check_for_nan(y0, x0, nodes_dict[n]['y'], nodes_dict[n]['x'])
                if dist <= radius:
                    cropped_node_list.append(n)
            if 0 < len(cropped_node_list) < len(e['nodes']):
                if 'left_border' in e:
                    e['left_border'] = border_within_box(x0, y0, e['left_border'], radius)
                if 'right_border' in e:
                    e['right_border'] = border_within_box(x0, y0, e['right_border'], radius)

            e['nodes'] = cropped_node_list


def remove_elements_beyond_radius(elements, nodes_dict, x0, y0, radius):
    """
    Remove elements of a list having coordinates beyond certain radius
    :param elements: list of elements
    :param nodes_dict: dictionary
    :param x0: center coordinate
    :param y0: center coordinate
    :param radius: radius in meters
    :return: list of remaining elements
    """

    for e in elements:
        if e['type'] != 'node':

            e['cropped'] = 'no'

            if 'left_border' in e:
                e['length'] = get_border_length(e['left_border'])
            else:
                e['length'] = 0

            cropped_node_list = []
            for n in e['nodes']:
                dist = great_circle_vec_check_for_nan(y0, x0, nodes_dict[n]['y'], nodes_dict[n]['x'])
                if dist <= radius:
                    cropped_node_list.append(n)

            if 0 < len(cropped_node_list) < len(e['nodes']):
                e['cropped'] = 'yes'
                if 'left_border' in e:
                    e['left_border'] = border_within_box(x0, y0, e['left_border'], radius)
                    e['length'] = get_border_length(e['left_border'])
                if 'right_border' in e:
                    e['right_border'] = border_within_box(x0, y0, e['right_border'], radius)
                if 'median' in e:
                    e['median'] = border_within_box(x0, y0, e['median'], radius)

                if len(e['left_border']) < 1 or len(e['right_border']) < 1:
                    e['nodes'] = []
                    logger.debug('Unable to obtain the portion of the path %d within radius. Skipping.' % e['id'])
                    continue

                if 'name' in e['tags']:
                    street_name = set([e['tags']['name']])
                else:
                    street_name = set(['no_name'])

                if 'tags' in e and 'split' in e['tags'] and e['tags']['split'] == 'no':
                    x = (e['left_border'][-1][0] + e['right_border'][-1][0]) / 2.0
                    y = (e['left_border'][-1][1] + e['right_border'][-1][1]) / 2.0
                else:
                    x = e['left_border'][-1][0]
                    y = e['left_border'][-1][1]
                yy = nodes_dict[cropped_node_list[-1]]['y']
                xx = nodes_dict[cropped_node_list[-1]]['x']
                if great_circle_vec_check_for_nan(yy, xx, y, x) > 5.0:
                    cropped_node_list.append(create_a_node_from_coordinates((x,y), nodes_dict, street_name)['osmid'])

                if 'tags' in e and 'split' in e['tags'] and e['tags']['split'] == 'no':
                    x = (e['left_border'][0][0] + e['right_border'][0][0]) / 2.0
                    y = (e['left_border'][0][1] + e['right_border'][0][1]) / 2.0
                else:
                    x = e['left_border'][0][0]
                    y = e['left_border'][0][1]

                yy = nodes_dict[cropped_node_list[0]]['y']
                xx = nodes_dict[cropped_node_list[0]]['x']
                if great_circle_vec_check_for_nan(yy, xx, y, x) > 5.0:
                    new_node = create_a_node_from_coordinates((x, y), nodes_dict, street_name)
                    cropped_node_list = [new_node['osmid']] + cropped_node_list

            e['nodes'] = cropped_node_list

    return [e for e in elements if e['type'] == 'node' or len(e['nodes']) > 0 and e['length'] > 5.0]


def set_font_size(ax, font_size=14):
    """
    Set font size
    """
    for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] + ax.get_xticklabels() + ax.get_yticklabels()):
        item.set_fontsize(font_size)


def get_polygon_from_lane(lane,
                          fc='#808080',
                          ec='#000000',
                          alpha=1.0,
                          linestyle='dashed',
                          joinstyle='round',
                          fill=True,
                          hatch=None
                          ):
    """
    Get a polygon from a lane
    """
    if 'rail' not in lane['lane_type'] and 'cycleway' not in lane['lane_type']:
        if lane['direction'] == 'to_intersection':
            fc = '#003366'
        elif lane['direction'] == 'from_intersection':
            fc = '#006600'

    if lane['left_shaped_border'] is not None and lane['right_shaped_border'] is not None and 'L' in lane['lane_id']:
        polygon_sequence = lane['left_shaped_border'] + lane['right_shaped_border'][::-1]
    else:
        polygon_sequence = lane['left_border'] + lane['right_border'][::-1]

    polygon_sequence = lane['left_border'] + lane['right_border'][::-1]

    return Polygon(polygon_sequence,
                   closed=True,
                   fc=fc,
                   ec=ec,
                   alpha=alpha,
                   linestyle=linestyle,
                   joinstyle=joinstyle,
                   hatch=hatch,
                   fill=fill
                   )


def plot_lanes(lanes,
               fig=None,
               ax=None,
               cropped_intersection=None,
               fig_height=15,
               fig_width=15,
               axis_off=False,
               edge_linewidth=1,
               margin=0.02,
               linestyle='dashed',
               bgcolor='#CCFFE5',
               edge_color='#FF9933',
               fcolor='#808080',
               alpha=1.0,
               fill=True,
               hatch=None,
               ):
    """
    Plot lanes for existing street plot
    :param lanes:
    :param fig:
    :param ax:
    :param cropped_intersection:
    :param fig_height:
    :param fig_width:
    :param axis_off:
    :param edge_linewidth:
    :param margin:
    :param bgcolor:
    :param edge_color:
    :param alpha:
    :return:
    """

    if fig is None or ax is None:
        if cropped_intersection is None:
            return None, None

        g1 = graph_from_jsons(cropped_intersection, retain_all=True, simplify=False)
        fig, ax = ox.plot_graph(g1, fig_height=fig_height,
                                fig_width=fig_width,
                                axis_off=axis_off,
                                edge_linewidth=edge_linewidth,
                                margin=margin,
                                bgcolor=bgcolor,
                                edge_color=edge_color,
                                show=False
                                )

    for lane_data in lanes:
        if hatch is None and 'rail' in lane_data['lane_type']:
            track_hatch = track_symbol[lane_data['compass']]
        else:
            track_hatch = hatch

        if 'rail' in lane_data['lane_type']:
            lane_edge_color = '#000000'
        else:
            lane_edge_color = edge_color

        ax.add_patch(get_polygon_from_lane(lane_data,
                                           alpha=alpha,
                                           ec=lane_edge_color,
                                           fc=fcolor,
                                           fill=fill,
                                           hatch=track_hatch,
                                           linestyle=linestyle,)
                     )

    return fig, ax


def graph_from_jsons(response_jsons, network_type='all_private', simplify=True,
                     retain_all=False, truncate_by_edge=False, name='unnamed',
                     timeout=180, memory=None,
                     max_query_area_size=50 * 1000 * 50 * 1000,
                     clean_periphery=True, infrastructure='way["highway"]'):
    """
    Create a networkx graph from OSM data within the spatial boundaries of the passed-in shapely polygon.
    This is a modified routine from osmnx
    Parameters
    ----------
    response_jsons : list of responses from osmnx
        the shape to get network data within. coordinates should be in units of
        latitude-longitude degrees.
    network_type : string
        what type of street network to get
    simplify : bool
        if true, simplify the graph topology
    retain_all : bool
        if True, return the entire graph even if it is not connected
    truncate_by_edge : bool
        if True retain node if it's outside bbox but at least one of node's
        neighbors are within bbox
    name : string
        the name of the graph
    timeout : int
        the timeout interval for requests and to pass to API
    memory : int
        server memory allocation size for the query, in bytes. If none, server
        will use its default allocation size
    max_query_area_size : float
        max size for any part of the geometry, in square degrees: any polygon
        bigger will get divided up for multiple queries to API
    clean_periphery : bool
        if True (and simplify=True), buffer 0.5km to get a graph larger than
        requested, then simplify, then truncate it to requested spatial extent
    infrastructure : string
        download infrastructure of given type (default is streets (ie, 'way["highway"]') but other
        infrastructures may be selected like power grids (ie, 'way["power"~"line"]'))
    Returns
    -------
    networkx multidigraph
    """

    if clean_periphery and simplify:

        g_buffered = ox.create_graph(response_jsons, name=name, retain_all=True, network_type=network_type)

        # simplify the graph topology
        g = ox.simplify_graph(g_buffered)

        # count how many street segments in buffered graph emanate from each
        # intersection in un-buffered graph, to retain true counts for each
        # intersection, even if some of its neighbors are outside the polygon
        g.graph['streets_per_node'] = ox.count_streets_per_node(g, nodes=g.nodes())

    else:

        # create the graph from the downloaded data
        g = ox.create_graph(response_jsons, name=name, retain_all=True, network_type=network_type)

        # simplify the graph topology as the last step. don't truncate after
        # simplifying or you may have simplified out to an endpoint beyond the
        # truncation distance, in which case you will then strip out your entire
        # edge
        if simplify:
            g = ox.simplify_graph(g)

    return g
