#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module creates intersection data structure
#
#######################################################################

import osmnx as ox
from matplotlib.patches import Polygon
from path import add_borders_to_paths, split_bidirectional_paths, clean_paths, remove_zero_length_paths, set_direction
from node import get_nodes_dict, get_center, get_node_subset, get_intersection_nodes
from street import select_close_nodes


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


def get_intersection_data(paths, nodes_dict, street_tuple, size=500.0, crop_radius=150.0):

    intersection_nodes = select_close_nodes(nodes_dict, get_intersection_nodes(paths, street_tuple))
    u, v = get_center(intersection_nodes, nodes_dict)

    north, south, east, west = get_box(u, v, size=size)
    intersection_jsons = ox.osm_net_download(north=north, south=south, east=east, west=west, network_type='drive')
    intersection_paths = [e for e in intersection_jsons[0]['elements'] if e['type'] == 'way']
    correction(intersection_paths)
    node_subset = get_node_subset(intersection_jsons, intersection_paths)
    oneway_paths = add_borders_to_paths(split_bidirectional_paths(intersection_paths), nodes_dict)
    cleaned_intersection_paths = remove_zero_length_paths(clean_paths(oneway_paths, street_tuple))
    set_direction(cleaned_intersection_paths, u, v, nodes_dict)

    intersection_selection = [{'version': intersection_jsons[0]['version'],
                               'osm3s': intersection_jsons[0]['osm3s'],
                               'generator': intersection_jsons[0]['generator'],
                               'elements': node_subset
                               + cleaned_intersection_paths
                               }
                              ]

    cropped_intersection = crop_selection(intersection_selection, u, v, crop_radius)
    return cleaned_intersection_paths, cropped_intersection


def crop_selection(selection, x0, y0, radius=275.0):
    node_d = get_nodes_dict(selection)
    cropped_selection = []

    for s in selection:
        s_cropped = {'version': s['version'],
                     'osm3s': s['osm3s'],
                     'generator': s['generator'],
                     'elements': s['elements']
                     }
        for e in s_cropped['elements']:
            if e['type'] != 'node':
                cropped_node_list = []
                for n in e['nodes']:
                    dist = ox.great_circle_vec(y0, x0, node_d[n]['y'], node_d[n]['x'])
                    if dist <= radius:
                        cropped_node_list.append(n)
                e['nodes'] = cropped_node_list

        lst = [e for e in s_cropped['elements'] if e['type'] == 'node' or len(e['nodes']) > 1]
        s_cropped['element'] = lst
        cropped_selection.append(s_cropped)

    return cropped_selection


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


def get_polygon_from_lane(lane, fc='#808080', ec='w', alpha=1.0, linestyle='dashed', joinstyle='round'):
    """
    Get a polygon from a lane
    """
    if lane['direction'] == 'to_intersection':
        fc = '#003366'
    elif lane['direction'] == 'from_intersection':
        fc = '#00994C'

    if lane['left_shaped_border'] is not None and lane['left_shaped_border'] is not None and 'L' in lane['lane_id']:
        polygon_sequence = lane['left_shaped_border'] + lane['right_shaped_border'][::-1]
    else:
        polygon_sequence = lane['left_border'] + lane['right_border'][::-1]

    return Polygon(polygon_sequence,
                   closed=True,
                   fc=fc,
                   ec=ec,
                   alpha=alpha,
                   linestyle=linestyle,
                   joinstyle=joinstyle
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
               bgcolor='#CCFFE5',
               edge_color='#FF9933',
               alpha=1.0
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

    for lane in lanes:
        ax.add_patch(get_polygon_from_lane(lane, alpha=alpha))

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
