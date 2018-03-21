#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module creates intersection data structure
#
#######################################################################

import osmnx as ox
import copy
from matplotlib.patches import Polygon
from path import add_borders_to_paths, split_bidirectional_paths, clean_paths, remove_zero_length_paths, set_direction
from node import get_nodes_dict, get_center, get_node_subset, get_intersection_nodes, add_nodes_to_dictionary
from street import select_close_nodes

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


def create_intersection(street_tuple, city_data, size=500.0, crop_radius=150.0):
    """
    Create dictionary of intersection data.
    :param street_tuple: tuple of strings
    :param city_data: dictionary
    :param size: float in meters: initial size of osm data
    :param crop_radius: float in meters: the data within the initial size will be cropped to the specified radius
    :return: dictionary
    """
    x_nodes = select_close_nodes(city_data['nodes'], get_intersection_nodes(city_data['paths'], street_tuple))
    u, v = get_center(x_nodes, city_data['nodes'])

    north, south, east, west = get_box(u, v, size=size)
    x_data = {
        'city': city_data['name'],
        'streets': street_tuple,
        'center_x': u,
        'center_y': v,
        'north': north,
        'south': south,
        'east': east,
        'west': west,
        'size': size,
        'crop_radius': crop_radius
        }

    return x_data


def get_intersection_data(x_data, nodes_dict):
    """
    Get a list of paths related to the intersection and a list of data matching the osmnx format.
    :param x_data: dictionary
    :param nodes_dict: dictionary
    :return: a tuple of lists
    """
    intersection_jsons = ox.osm_net_download(north=x_data['north'],
                                             south=x_data['south'],
                                             east=x_data['east'],
                                             west=x_data['west'],
                                             network_type='drive'
                                             )
    intersection_paths = [e for e in intersection_jsons[0]['elements'] if e['type'] == 'way']
    add_nodes_to_dictionary([e for e in intersection_jsons[0]['elements'] if e['type'] == 'node'], nodes_dict)

    cropped_paths = remove_elements_beyond_radius(intersection_paths,
                                                  nodes_dict,
                                                  x_data['center_x'],
                                                  x_data['center_y'],
                                                  x_data['crop_radius']
                                                  )
    correction(cropped_paths)

    node_subset = get_node_subset(intersection_jsons, cropped_paths, nodes_dict)
    oneway_paths = add_borders_to_paths(split_bidirectional_paths(cropped_paths, nodes_dict), nodes_dict)
    cleaned_intersection_paths = remove_zero_length_paths(clean_paths(oneway_paths, x_data['streets']))
    set_direction(cleaned_intersection_paths, x_data['center_x'], x_data['center_y'], nodes_dict)

    intersection_selection = [{'version': intersection_jsons[0]['version'],
                               'osm3s': intersection_jsons[0]['osm3s'],
                               'generator': intersection_jsons[0]['generator'],
                               'elements': node_subset
                               + cleaned_intersection_paths
                               }
                              ]

    return cleaned_intersection_paths, intersection_selection


def get_railway_data(x_data, nodes_dict):
    """
    Get railway data if applicable for the intersection and crop within the radius.
    :param x_data: dictionary
    :param nodes_dict: dictionary 
    :return: list of railway paths 
    """
    railway_jsons = ox.osm_net_download(north=x_data['north'],
                                        south=x_data['south'],
                                        east=x_data['east'],
                                        west=x_data['west'],
                                        network_type='all',
                                        infrastructure='way["railway"]'
                                        )
    railway_paths = [e for e in railway_jsons[0]['elements'] if e['type'] == 'way']
    add_nodes_to_dictionary([e for e in railway_jsons[0]['elements'] if e['type'] == 'node'], nodes_dict)
    cropped_paths = remove_elements_beyond_radius(railway_paths,
                                                  nodes_dict,
                                                  x_data['center_x'],
                                                  x_data['center_y'],
                                                  x_data['crop_radius']
                                                  )
    paths_with_borders = add_borders_to_paths(cropped_paths, nodes_dict, width=2.0)
    set_direction(paths_with_borders, x_data['center_x'], x_data['center_y'], nodes_dict)
    return paths_with_borders


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
            cropped_node_list = []
            for n in e['nodes']:
                dist = ox.great_circle_vec(y0, x0, nodes_dict[n]['y'], nodes_dict[n]['x'])
                if dist <= radius:
                    cropped_node_list.append(n)
            e['nodes'] = cropped_node_list

    return [e for e in elements if e['type'] == 'node' or len(e['nodes']) > 1]


def get_box(x, y, size=500.0):
    north_south = 0.0018
    dist = ox.great_circle_vec(y, x, y + north_south, x)
    scale = size / dist
    north = y + north_south * scale
    south = y - north_south * scale

    east_west = 0.00227
    dist = ox.great_circle_vec(y, x, y, x + east_west)
    scale = size / dist
    west = x - east_west * scale
    east = x + east_west * scale

    return north, south, east, west


def correction(paths):
    for p in paths:
        if p['id'] == 517844779:
            p['tags']['lanes'] = 4
            p['tags']['turn:lanes'] = 'left|||'

        if p['id'] == 45097701:
            p['tags']['lanes'] = 2


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
    if 'rail' not in lane['lane_type']:
        if lane['direction'] == 'to_intersection':
            fc = '#003366'
        elif lane['direction'] == 'from_intersection':
            fc = '#00994C'

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
        """
        if lane_data['approach_id'] == 0:
            track_hatch = '0'
        else:
            track_hatch = '|'
        """
        ax.add_patch(get_polygon_from_lane(lane_data,
                                           alpha=alpha,
                                           ec=edge_color,
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
