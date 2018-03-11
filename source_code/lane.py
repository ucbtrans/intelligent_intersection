#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module creates lanes for the intersection
#
#######################################################################


import copy
import math
import shapely.geometry as geom
from border import shift_list_of_nodes, get_incremental_points, extend_vector, cut_border_by_polygon, set_lane_bearing
from path import get_num_of_lanes, count_lanes


def get_turn_type(origin_lane, destination_lane):
    """
    Identify the guideway direction as a left turn (including U-turn), through, or right turn.
    The direction +/- 45 degree from the origin compass bearing considered as a trough direction.
    All other directions considered as turns.
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :return: string
    """

    turn_angle = (destination_lane['bearing'] - origin_lane['bearing'] + 360.0) % 360

    if turn_angle > 225.0:
        return 'left_turn'
    elif turn_angle < 135.0:
        return 'right_turn'
    else:
        return 'through'


def add_space_for_crosswalk(lane, crosswalk_width=1.82):
    """
    Extend space around the lane to include a crosswalk into the space
    :param lane: dictionary
    :param crosswalk_width: float
    :return: dictionary
    """
    return lane['left_border'], shift_list_of_nodes(lane['right_border'], [crosswalk_width]*len(lane['right_border']))


def shorten_lane_for_crosswalk(lane, lanes, crosswalk_width=1.82):
    """
    Remove the portion of the lane border overlapping with any crosswalk crossing the lane border.
    Scan all lanes with street names other than the street the lane border belongs to,
    and identify crosswalks related to each lane.
    :param lane: dictionary
    :param lanes: list of dictionaries
    :param crosswalk_width: float
    :return: dictionary
    """
    if lane['left_shaped_border'] is None:
        border_name = '_border'
    else:
        border_name = '_shaped_border'

    for l in lanes:
        if l['name'] == 'no_name' or l['name'] == lane['name']:
            continue

        if l['lane_id'] == '1' or l['lane_id'] == '1R':

            lb, rb = add_space_for_crosswalk(l, crosswalk_width=crosswalk_width)
            coord = lb + rb[::-1]
            polygon = geom.Polygon(coord)
            lane['left_shaped_border'] = cut_border_by_polygon(lane['left' + border_name], polygon)
            lane['right_shaped_border'] = cut_border_by_polygon(lane['right' + border_name], polygon)
            border_name = '_shaped_border'
    return lane


def shorten_lanes(lanes, crosswalk_width=1.82):
    for lane in lanes:
        if lane['name'] == 'no_name' and 'L' not in lane['lane_id']:
            continue
        shorten_lane_for_crosswalk(lane, lanes, crosswalk_width=crosswalk_width)


def get_lane_index_from_left(lane):
    """
    Calculate lane index (number) from the most left lane.
    Assuming that the origin and destination lanes must have the same lane index from left,
    i.e. the driver is obeying the rules and turning from the most left origin lane to the most left one, and so on.
    The destination lane in some rare cases can be a turn lane for the next intersection.
    So we identify the destination lane by the index from left rather than by the lane id.
    :param lane: lane dictionary
    :return: number - zero based: the most left lane index is zero.
    """

    if lane['direction'] == 'to_intersection':
        path_index = -1
    else:
        path_index = 0
    if isinstance(lane['path'], list):
        num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(lane['path'][path_index])
    else:
        num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(lane['path'])

    if 'L' in lane['lane_id']:
        return num_of_left_lanes - int(lane['lane_id'][0])
    elif 'R' in lane['lane_id']:
        total_lanes = num_of_left_lanes + num_of_right_lanes + num_of_trunk_lanes
        return total_lanes - int(lane['lane_id'][0])
    else:
        return num_of_left_lanes + num_of_trunk_lanes - int(lane['lane_id'][0])


def get_lane_index_from_right(lane):
    """
    Calculate lane index (number) from the most right lane.
    :param lane: dictionary
    :return: number - zero based: the most right lane index is zero.
    """
    if lane['direction'] == 'to_intersection':
        path_index = -1
    else:
        path_index = 0
    if isinstance(lane['path'], list):
        num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(lane['path'][path_index])
    else:
        num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(lane['path'])

    if 'L' in lane['lane_id']:
        return num_of_right_lanes + num_of_trunk_lanes + int(lane['lane_id'][0]) - 1
    elif 'R' in lane['lane_id']:
        return int(lane['lane_id'][0]) - 1
    else:
        return num_of_right_lanes + int(lane['lane_id'][0]) - 1


def add_incremental_points(border, n=10, l=6.0):
    """
    Insert intermediates coordinates in the beginning of a coordinate list
    :param border: coordinate list
    :param n: number of points to insert
    :param l: combined length of n additional points
    :return: updated list of coordinates
    """
    if len(border) < 2:
        return border

    return border[:1] + get_incremental_points(border[0], border[1], n, l)[1:] + border[1:]


def get_shaped_lane_width(width, n=10):
    return [abs(1.0 - (math.cos(i/float(n)*math.pi) + 1.0)/2.0)*width for i in range(n+1)]


def create_lane(p, nodes_dict,
                left_border=None,
                right_border=None,
                right_shaped_border=None,
                lane_id=1,
                lane_type='',
                direction='undefined',
                width=3.048,
                shape_points=16,
                shape_length=10.0,
                num_of_left_lanes=0,
                num_of_right_lanes=0,
                num_of_trunk_lanes=1,
                crosswalk_width=1.82
                ):

    lane = {
        'lane_id': str(lane_id),
        'path_id': p['id'],
        'path': p,
        'left_border': copy.deepcopy(left_border),
        'lane_type': lane_type,
        'direction': direction,
        'width': width,
        'shape_points': shape_points,
        'shape_length': shape_length,
        'num_of_left_lanes': num_of_left_lanes,
        'num_of_right_lanes': num_of_right_lanes,
        'num_of_trunk_lanes': num_of_trunk_lanes,
        'crosswalk_width': crosswalk_width
    }

    for x in p['tags']:
        lane[x] = p['tags'][x]

    if lane_type == 'left':
        lane['lane_id'] = str(lane_id) + 'L'
    elif lane_type == 'right':
        lane['lane_id'] = str(lane_id) + 'R'

    if 'name' in p['tags']:
        name = p['tags']['name']
    else:
        name = 'no_name'

    lane['name'] = name
    lane['nodes'] = p['nodes']
    lane['nodes_coordinates'] = [(nodes_dict[n]['x'], nodes_dict[n]['y']) for n in lane['nodes']]
    lane['right_shaped_border'] = None
    lane['left_shaped_border'] = None

    if right_border is None:
        lane['left_border'] = copy.deepcopy(left_border)
        lane['right_border'] = shift_list_of_nodes(left_border, [width]*len(left_border))
    elif left_border is None:
        lane['right_border'] = copy.deepcopy(right_border)
        lane['left_border'] = shift_list_of_nodes(right_border, [-width]*len(right_border))

        if 'L' in lane['lane_id']:
            right_border_with_inserted_points = add_incremental_points(right_border, n=shape_points, l=shape_length)
            delta_len = len(right_border_with_inserted_points) - len(right_border)
            shaped_widths = get_shaped_lane_width(-width, n=shape_points)
            width_list = shaped_widths[:delta_len] + [-width]*len(right_border)
            if lane['lane_id'] == '1L':
                lane['right_shaped_border'] = copy.deepcopy(lane['right_border'])
                lane['left_shaped_border'] = shift_list_of_nodes(right_border_with_inserted_points, width_list)
            elif right_shaped_border is not None:
                lane['right_shaped_border'] = copy.deepcopy(right_shaped_border)
                lane['left_shaped_border'] = shift_list_of_nodes(right_shaped_border, width_list,
                                                                 direction_reference=lane['right_border']
                                                                 )
    else:
        lane['right_border'] = copy.deepcopy(right_border)
        lane['left_border'] = copy.deepcopy(left_border)

    if 'L' not in lane['lane_id']:
        lane['right_shaped_border'] = None
        lane['left_shaped_border'] = None

    return lane


def add_lane(lane, merged_lane=None):

    if merged_lane is None:
        merged_lane = {
            'width': [lane['width']],
            'path_id': [lane['path_id']],
            'path': [lane['path']],
            'nodes': copy.deepcopy(lane['nodes']),
            'left_border': copy.deepcopy(lane['left_border']),
            'right_border': copy.deepcopy(lane['right_border']),
            'nodes_coordinates': copy.deepcopy(lane['nodes_coordinates']),
            'right_shaped_border': copy.deepcopy(lane['right_shaped_border']),
            'left_shaped_border': copy.deepcopy(lane['left_shaped_border']),
            'shape_points': copy.deepcopy(lane['shape_points']),
            'shape_length': copy.deepcopy(lane['shape_length']),
        }
    else:
        for k in ['nodes', 'left_border', 'right_border', 'nodes_coordinates']:
            merged_lane[k] += lane[k][1:]
        for k in ['width', 'path_id', 'path']:
            merged_lane[k] += [lane[k]]

        if merged_lane['right_shaped_border'] is not None:
            merged_lane['right_shaped_border'] += lane['right_border']
        if merged_lane['left_shaped_border'] is not None:
            merged_lane['left_shaped_border'] += lane['left_border']

    for k in lane:
        if k not in ['width',
                     'path_id',
                     'path',
                     'nodes',
                     'left_border',
                     'right_border',
                     'nodes_coordinates',
                     'right_shaped_border',
                     'left_shaped_border',
                     'shape_length',
                     'shape_points']:
            merged_lane[k] = lane[k]
    return merged_lane


def get_next_right_lane(lane, lanes):
    next_lanes = [l for l in lanes
                  if l['name'] == lane['name']
                  and l['direction'] == lane['direction']
                  and lane['nodes'][0] in l['nodes'][:-1]
                  and get_lane_index_from_left(lane) + 1 == get_lane_index_from_left(l)
                  ]
    if len(next_lanes) > 0:
        return next_lanes[0]
    return None


def reshape_lane(lane, lanes):
    """
    Reapply starting shapes to a lane
    :param lane: dictionary
    :param lanes: list of dictionaries
    :return: None
    """
    if 'L' in lane['lane_id'] and '1L' not in lane['lane_id']:
        next_to_right = get_next_right_lane(lane, lanes)

        if next_to_right is not None and 'prev' in next_to_right and next_to_right['prev'] is not None:

            right_border_with_inserted_points = add_incremental_points(lane['right_border'],
                                                                       n=lane['shape_points'],
                                                                       l=lane['shape_length']
                                                                       )
            delta_len = len(right_border_with_inserted_points) - len(lane['right_border'])
            shaped_widths = get_shaped_lane_width(-lane['width'], n=lane['shape_points'])
            width_list = shaped_widths[:delta_len] + [-lane['width']] * len(lane['right_border'])
            lane['left_shaped_border'] = shift_list_of_nodes(right_border_with_inserted_points, width_list)
            lane['right_shaped_border'] = copy.deepcopy(lane['right_border'])


def reshape_lanes(lanes):
    """
    Reapply starting shapes to existing lanes
    :param lanes: list of dictionaries
    :return: None
    """
    for lane in lanes:
        reshape_lane(lane, lanes)


def extend_origin_left_border(lane, all_lanes):
    """
    Extend the last section of the left border to a large size in order to find cross points with other lanes
    :param lane: lane dictionary
    :param all_lanes: list of dictionaries
    :return: list of coordinates representing new extended border
    """

    shorten_lane_for_crosswalk(lane, all_lanes)

    return lane['left_shaped_border'][:-2] + extend_vector(lane['left_shaped_border'][-2:], backward=False)


def extend_destination_left_border(lane):
    """
    Extend the last section of the left border to a large size in order to find cross points with other lanes
    :param lane: destination lane
    :return: left border extended backwards
    """
    return extend_vector(lane['left_border'][:2]) + lane['left_border'][2:]


def intersects(origin_lane, destination_lane, all_lanes):
    """
    Check if two lanes intersects.
    Definition of intersection: the destination lane has a common node with any lane
    belonging to the origin street.  The destination lane does necessarily crosses the origin lane
    but it may cross another lane from the origin street to satisfy the intersection requirement.
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :return: True if there is a common node, False otherwise
    """
    origin_nodes = []
    origin_street_lanes = [ll for ll in all_lanes if ll['name'] == origin_lane['name']]
    [origin_nodes.extend(l['nodes']) for l in origin_street_lanes]
    origin_nodes_set = set(origin_nodes)
    if len([n for n in destination_lane['nodes'] if n in origin_nodes_set]) > 0:
        return True
    else:
        return False


def get_lanes(paths, nodes_dict, shape_points=16, shape_length=10.0):
    lanes = []
    for p in paths:
        lanes.extend(get_lanes_from_path(p, nodes_dict, shape_points=shape_points, shape_length=shape_length))

    return lanes


def get_lanes_from_path(p, nodes_dict, shape_points=16, shape_length=10.0):

    if len(p['nodes']) < 2:
        return []

    lanes = []

    num_of_lanes = get_num_of_lanes(p)

    if 'turn:lanes' in p['tags']:
        lane_types = p['tags']['turn:lanes'].split('|')
    else:
        lane_types = [''] * num_of_lanes

    lane_types = lane_types[::-1]
    left_border = copy.deepcopy(p['left_border'])
    num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(p)

    for i in range(num_of_lanes, 0, -1):
        if lane_types[i - 1] == 'left':
            continue
        lane = create_lane(p, nodes_dict,
                           left_border=left_border,
                           lane_id=i,
                           lane_type=lane_types[i - 1],
                           direction=p['tags']['direction'],
                           shape_points=shape_points, shape_length=shape_length,
                           num_of_left_lanes=num_of_left_lanes,
                           num_of_right_lanes=num_of_right_lanes,
                           num_of_trunk_lanes=num_of_trunk_lanes
                           )
        lanes.append(lane)
        left_border = lane['right_border']

    right_border = copy.deepcopy(p['left_border'])
    right_shaped_border = right_border
    for i in range(num_of_left_lanes):
        lane = create_lane(p, nodes_dict,
                           right_border=right_border,
                           lane_id=i + 1,
                           lane_type='left',
                           direction=p['tags']['direction'],
                           right_shaped_border=right_shaped_border,
                           shape_points=shape_points, shape_length=shape_length,
                           num_of_left_lanes=num_of_left_lanes,
                           num_of_right_lanes=num_of_right_lanes,
                           num_of_trunk_lanes=num_of_trunk_lanes
                           )
        lanes.append(lane)
        right_border = lane['left_border']
        right_shaped_border = lane['left_shaped_border']

    return lanes


def merge_lanes(lanes):

    merged_lanes = []
    for lane in [l for l in lanes if l['name'] == 'no_name']:
        merged_lanes.append(add_lane(lane, merged_lane=None))

    names = set([l['name'] for l in lanes if l['name'] != 'no_name'])
    for name in names:
        ids = sorted(set([l['lane_id'] for l in lanes if l['name'] == name]))
        for lane_id in ids:
            directions = set([l['direction'] for l in lanes if l['lane_id'] == lane_id and l['name'] == name])
            for direction in directions:
                similar_lanes = [l for l in lanes
                                 if l['lane_id'] == lane_id
                                 and l['name'] == name
                                 and l['direction'] == direction
                                 and len(l['nodes']) > 1
                                 ]
                for similar_lane in similar_lanes:
                    next_lanes = [l for l in similar_lanes if similar_lane['nodes'][-1] == l['nodes'][0]]
                    if len(next_lanes) == 0:
                        similar_lane['next'] = None
                    else:
                        similar_lane['next'] = next_lanes[0]['path_id']

                    prev_lanes = [l for l in similar_lanes if similar_lane['nodes'][0] == l['nodes'][-1]]
                    if len(prev_lanes) == 0:
                        similar_lane['prev'] = None
                    else:
                        similar_lane['prev'] = prev_lanes[0]['path_id']

                reshape_lanes(lanes)

                for start_lane in [l for l in similar_lanes if l['prev'] is None]:
                    merged_lane = add_lane(start_lane, merged_lane=None)
                    nxt = start_lane['next']
                    while nxt is not None:
                        next_lane = [l for l in similar_lanes if l['path_id'] == nxt][0]

                        merged_lane = add_lane(next_lane, merged_lane=merged_lane)

                        nxt = next_lane['next']

                    merged_lanes.append(merged_lane)

    set_lane_bearing(merged_lanes)
    set_approach_ids(merged_lanes)
    return merged_lanes


def set_approach_ids(merged_lanes):
    """
    Set approach ids for a list of merged lanes.  
    Approaches are numbered separately for each intersection starting from zero.
    :param merged_lanes: list of dictionaries
    :return: None
    """
    for n, m in enumerate(merged_lanes):
        m['approach_id'] = n
