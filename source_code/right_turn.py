#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module constructs right turn
#
#######################################################################


import shapely.geometry as geom
from border import cut_border_by_distance
from lane import get_lane_index_from_right, get_turn_type, intersects
from turn import construct_turn_arc, shorten_border_for_crosswalk


def is_right_turn_allowed(lane_data, all_lanes):
    if 'right' in lane_data['lane_type'] or 'R ' in lane_data['lane_id']:
        return True
    if lane_data['lane_id'] == '1' and lane_data['lane_type'] == '' and lane_data['direction'] == 'to_intersection':
        return True
    if lane_data['lane_type'] == 'through' \
            and lane_data['direction'] == 'to_intersection' \
            and len(get_connected_links(lane_data, all_lanes)) > 0:
        return True

    return False


def get_connected_links(origin_lane, all_lanes):
    """
    Get a list of trunk link lanes starting from the given origin lane.
    :param origin_lane: dictionary
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """
    return [l for l in all_lanes
            if 'highway' in l['path'][0]['tags']
            and l['path'][0]['tags']['highway'] == 'trunk_link'
            and l['nodes'][0] in origin_lane['nodes']
            and origin_lane['lane_id'][0] == l['lane_id'][0]
            ]


def get_link(origin_lane, all_lanes):
    links = get_connected_links(origin_lane, all_lanes)
    if len(links) > 0:
        return links[0]
    else:
        return None


def get_link_destination_lane(link_lane, all_lanes):
    """
    Get destination lane for a link
    :param link_lane: dictionary
    :param all_lanes: list of dictionaries
    :return: dictionary
    """
    res = [l for l in all_lanes
           if link_lane['nodes'][-1] in l['nodes']
           and link_lane['lane_id'] == l['lane_id']
           and l['direction'] == 'from_intersection'
           ]
    if len(res) > 0:
        return res[0]
    else:
        return None


def get_right_turn_border(origin_border, link_border, destination_border):
    """
    Construct either left or right border for a right turn via link
    :param origin_border: list of coordinates
    :param link_border: list of coordinates
    :param destination_border: list of coordinates
    :return: list of coordinates
    """
    origin_line = geom.LineString(origin_border)
    link_line = geom.LineString(link_border)
    if not origin_line.intersects(link_line):
        # Something went terribly wrong
        return None
    intersection_point1 = origin_line.intersection(link_line)
    origin_line1 = cut_border_by_distance(origin_line, origin_line.project(intersection_point1))[0]
    ct1 = cut_border_by_distance(link_line, link_line.project(intersection_point1))
    if len(ct1) < 2:
        return None

    link_line1 = ct1[1]

    destination_line = geom.LineString(destination_border)
    if not destination_line.intersects(link_line1):
        # Something went terribly wrong
        return None
    intersection_point2 = destination_line.intersection(link_line1)
    line2 = cut_border_by_distance(destination_line, destination_line.project(intersection_point2))[1]

    return list(origin_line1.coords) + link_border[1:-1] + list(line2.coords)


def get_destination_lanes_for_right_turn(origin_lane, all_lanes):
    """
    Identifying destination lanes (possibly more than one).
    Assuming that the origin and destination lanes must have the same lane index from right,
    i.e. the driver is obeying the rules and turning from the most right origin lane to the most right one, and so on.
    The destination lane in some rare cases can be a turn lane for the next intersection.
    So we identify the destination lane by the index from right rather than by the lane id.
    :param origin_lane: lane dictionary of a left turn
    :param all_lanes: list of dictionaries
    :return: list of valid lane destinations for the left turn
    """
    if origin_lane['name'] == 'no_name':
        return []
    if not is_right_turn_allowed(origin_lane, all_lanes):
        return []

    destination_index = get_lane_index_from_right(origin_lane)
    return [l for l in all_lanes
            if l['name'] != origin_lane['name']
            and l['name'] != 'no_name'
            and l['direction'] == 'from_intersection'
            and destination_index == get_lane_index_from_right(l)
            and intersects(origin_lane, l, all_lanes)
            and get_turn_type(origin_lane, l) == 'right_turn'
            ]


def get_direct_right_turn_border(origin_lane,
                                 destination_lane,
                                 all_lanes,
                                 border_type='left',
                                 turn_direction=1,
                                 angle_delta=0.0,
                                 use_shaped_border=False
                                 ):

    shaped_border = border_type + '_shaped_border'
    non_shaped_border = border_type + '_border'

    if not use_shaped_border:
        origin_border = origin_lane[non_shaped_border]
    elif shaped_border not in origin_lane or origin_lane[shaped_border] is None:
        origin_border = origin_lane[non_shaped_border]
    else:
        origin_border = origin_lane[shaped_border]

    destination_border = destination_lane[non_shaped_border]

    shorten_origin_border = shorten_border_for_crosswalk(origin_border,
                                                              origin_lane['name'],
                                                              all_lanes,
                                                              destination='to_intersection'
                                                              )
    shorten_destination_border = shorten_border_for_crosswalk(destination_border,
                                                              destination_lane['name'],
                                                              all_lanes,
                                                              destination='from_intersection'
                                                              )

    turn_arc = construct_turn_arc(shorten_origin_border,
                                  shorten_destination_border,
                                  turn_direction=turn_direction,
                                  angle_delta=angle_delta)
    if turn_arc is None:
        return None

    destination_line = geom.LineString(destination_border)
    landing_point = destination_line.project(geom.Point(turn_arc[-1]))
    landing_border = cut_border_by_distance(destination_line, landing_point)[1]

    return origin_border[:-1] + turn_arc + list(landing_border.coords)[1:]
