#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for railways
#
#######################################################################

import copy
from random import randint


def split_railways(rail_tracks, referenced_nodes):
    """
    Split railways in the list into pieces if they intersect with a street.
    Intersecting means a common node. 
    :param rail_tracks: list of dictionaries
    :param referenced_nodes: dictionary of nodes referenced in streets related to the intersection
    :return: list of dictionaries
    """

    split_tracks = []

    for track_data in rail_tracks:
        split = 'no'
        for i, n in enumerate(track_data['nodes']):
            if 0 < i < len(track_data['nodes']) and n in referenced_nodes:
                track1, track2 = split_track_by_node_index(track_data, i)
                split_tracks.append(track1)
                split_tracks.append(track2)
                split = 'yes'
                break
        track_data['tags']['cut'] = split

    split_tracks.extend([t for t in rail_tracks if 'cut' in t['tags'] and t['tags']['cut'] == 'no'])
    return split_tracks


def split_track_by_node_index(track_data, i):
    """
    Split a railway into two pieces by index in the node list.
    This is needed to separate a portion of the railway coming to the intersection from
    the rest of the railway exiting the intersection
    :param track_data: dictionary
    :param i: node index
    :return: a tuple of dictionaries
    """
    track1 = copy.deepcopy(track_data)
    track2 = copy.deepcopy(track_data)
    track1['nodes'] = track_data['nodes'][:i+1]
    track2['nodes'] = track_data['nodes'][i:]
    track1['id'] = ((track_data['id']) % 100000)*100000 + randint(0, 100000)
    track2['id'] = ((track_data['id']) % 100000)*100000 + randint(100000, 200000)
    if 'original_id' not in track_data:
        track1['original_id'] = track_data['id']
        track2['original_id'] = track_data['id']
    track1['tags']['cut'] = 'yes'
    track2['tags']['cut'] = 'yes'
    return track1, track2


def remove_subways(tracks):
    """
    Remove subway or underground tracks
    :param tracks: list of track dictionaries
    :return: list of track dictionaries without subway or underground tracks
    """
    tracks_without_subway = []
    for t in tracks:
        if 'tags' in t:
            if 'railway' in t['tags'] and t['tags']['railway'] == 'subway':
                continue
            if 'tunnel' in t['tags'] and t['tags']['tunnel'] == 'yes':
                continue
            if 'subway' in t['tags'] and t['tags']['subway'] == 'yes':
                continue
            if 'layer' in t['tags']:
                try:
                    l = int(t['tags']['layer'])
                except:
                    l = 0
                if l < 0:
                    continue
        tracks_without_subway.append(t)

    return tracks_without_subway


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
                                           linestyle=linestyle, )
                     )

    return fig, ax
