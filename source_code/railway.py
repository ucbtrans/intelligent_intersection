#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides functions for railways
#
#######################################################################

import copy


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
        track_data['tags']['split'] = split

    split_tracks.extend([t for t in rail_tracks if t['tags']['split'] == 'no'])
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
    track1['id'] = ((track1['id']) % 1000)*10 + 1
    track2['id'] = ((track1['id']) % 1000)*10 + 2
    if 'original_id' in track_data:
        track1['tags']['original_id'] = track_data['original_id']
        track2['tags']['original_id'] = track_data['original_id']
    else:
        track1['tags']['original_id'] = track_data['id']
        track2['tags']['original_id'] = track_data['id']
    track1['tags']['split'] = 'yes'
    track2['tags']['split'] = 'yes'
    return track1, track2
