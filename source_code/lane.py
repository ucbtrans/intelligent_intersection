#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module creates lanes for the intersection
#
#   Reference: https://wiki.openstreetmap.org/wiki/Map_Features
#
#######################################################################


import copy
import math
import shapely.geometry as geom
from border import shift_list_of_nodes, get_incremental_points, extend_vector, \
    cut_border_by_polygon, set_lane_bearing, get_angle_between_bearings, extend_both_sides_of_a_border, \
    get_border_length, get_distance_from_point_to_line
from path_way import get_num_of_lanes, count_lanes, reverse_direction
from bicycle import key_value_check, get_bicycle_lane_location, is_shared
from log import get_logger, dictionary_to_log


logger = get_logger()


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

    if turn_angle > 315.0:
        return 'u_turn'
    elif turn_angle > 225.0:
        return 'left_turn'
    elif 45.0 < turn_angle < 135.0:
        return 'right_turn'
    elif turn_angle < 45.0:
        return 'through'
    else:
        return None


def add_space_for_crosswalk(lane_data, crosswalk_width=1.82):
    """
    Extend space around the lane to include a crosswalk into the space
    :param lane_data: dictionary
    :param crosswalk_width: float
    :return: dictionary
    """
    left_border = extend_both_sides_of_a_border(lane_data['left_border'])
    right_border = extend_both_sides_of_a_border(lane_data['right_border'])

    return shift_list_of_nodes(left_border, [-crosswalk_width]*len(left_border)),\
        shift_list_of_nodes(right_border, [crosswalk_width]*len(right_border))


def shorten_lane_for_crosswalk(lane_data, lanes, crosswalk_width=1.82):
    """
    Remove the portion of the lane border overlapping with any crosswalk crossing the lane border.
    Scan all lanes with street names other than the street the lane border belongs to,
    and identify crosswalks related to each lane.
    :param lane_data: dictionary
    :param lanes: list of dictionaries
    :param crosswalk_width: float
    :return: dictionary
    """
    if lane_data['left_shaped_border'] is None:
        border_name = '_border'
    else:
        border_name = '_shaped_border'

    for l in lanes:
        if l['name'] == 'no_name' or l['name'] == lane_data['name']:
            continue

        if l['lane_id'] == '1' or l['lane_id'] == '1R':

            lb, rb = add_space_for_crosswalk(l, crosswalk_width=crosswalk_width)
            coord = lb + rb[::-1]
            polygon = geom.Polygon(coord)
            lane_data['left_shaped_border'] = cut_border_by_polygon(lane_data['left' + border_name], polygon)
            lane_data['right_shaped_border'] = cut_border_by_polygon(lane_data['right' + border_name], polygon)
            border_name = '_shaped_border'
    return lane_data


def shorten_lanes(lanes, crosswalk_width=1.82):
    for lane_data in lanes:
        if lane_data['name'] == 'no_name' and 'L' not in lane_data['lane_id']:
            continue
        shorten_lane_for_crosswalk(lane_data, lanes, crosswalk_width=crosswalk_width)


def get_lane_index_from_left(lane_data):
    """
    Calculate lane index (number) from the most left lane.
    Assuming that the origin and destination lanes must have the same lane index from left,
    i.e. the driver is obeying the rules and turning from the most left origin lane to the most left one, and so on.
    The destination lane in some rare cases can be a turn lane for the next intersection.
    So we identify the destination lane by the index from left rather than by the lane id.
    :param lane_data: lane dictionary
    :return: number - zero based: the most left lane index is zero.
    """

    if lane_data['direction'] == 'to_intersection':
        path_index = -1
    else:
        path_index = 0
    if isinstance(lane_data['path'], list):
        num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(lane_data['path'][path_index])
    else:
        num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(lane_data['path'])

    if 'L' in lane_data['lane_id']:
        return num_of_left_lanes - int(lane_data['lane_id'][0])
    elif 'R' in lane_data['lane_id']:
        total_lanes = num_of_left_lanes + num_of_right_lanes + num_of_trunk_lanes
        return total_lanes - int(lane_data['lane_id'][0])
    else:
        return num_of_left_lanes + num_of_trunk_lanes - int(lane_data['lane_id'][0])


def get_lane_index_from_right(lane_data):
    """
    Calculate lane index (number) from the most right lane.
    :param lane_data: dictionary
    :return: number - zero based: the most right lane index is zero.
    """
    if 'B' in lane_data['lane_id']:
        return 0

    if lane_data['direction'] == 'to_intersection':
        path_index = -1
    else:
        path_index = 0
    if isinstance(lane_data['path'], list):
        num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(lane_data['path'][path_index])
    else:
        num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(lane_data['path'])

    if 'L' in lane_data['lane_id']:
        return num_of_right_lanes + num_of_trunk_lanes + int(lane_data['lane_id'][0]) - 1
    elif 'R' in lane_data['lane_id']:
        return int(lane_data['lane_id'][0]) - 1
    else:
        return num_of_right_lanes + int(lane_data['lane_id'][0]) - 1


def get_most_right_lane(lanes, name, direction, bearing):
    """
    Get the most right lane for a street for the specified direction
    :param lanes: list of lane dictionaries
    :param name: string
    :param direction: string
    :param bearing: float
    :return: lane dictionary
    """
    for l in lanes:
        if l['name'] == name and l['direction'] == direction and get_lane_index_from_right(l) == 0:
            if abs(get_angle_between_bearings(bearing, l['bearing'])) < 15:
                return l
    return None


def get_most_left_lane(lanes, name, direction, bearing):
    """
    Get the most left lane for a street for the specified direction
    :param lanes: list of lane dictionaries
    :param name: string
    :param direction: string
    :param bearing: float
    :return: lane dictionary
    """
    for l in lanes:
        if l['name'] == name and l['direction'] == direction and get_lane_index_from_left(l) == 0:
            if abs(get_angle_between_bearings(bearing, l['bearing'])) < 15:
                return l
    return None


def get_sorted_lane_subset(lanes, name, bearing, direction, func):
    """
    Get subset of lanes for the specified name, bearing ang direction.
    Sort the results fy the specified function.
    :param lanes: list of lanes
    :param name: string
    :param bearing: float in degrees
    :param direction: string
    :param func: function name to provide sorting value
    :return: list of lanes
    """

    subset = [l for l in lanes if l['name'] == name
              and l['direction'] == direction
              and abs(get_angle_between_bearings(bearing, l['bearing'])) < 30
              ]

    if subset:
        return sorted(subset, key=func)
    else:
        return []


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


def create_lane(p,
                nodes_dict,
                left_border=None,
                right_border=None,
                right_shaped_border=None,
                lane_id='1',
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
    """
    Create a lane from a path
    :param p: 
    :param nodes_dict: 
    :param left_border: 
    :param right_border: 
    :param right_shaped_border: 
    :param lane_id: 
    :param lane_type: 
    :param direction: 
    :param width: 
    :param shape_points: 
    :param shape_length: 
    :param num_of_left_lanes: 
    :param num_of_right_lanes: 
    :param num_of_trunk_lanes: 
    :param crosswalk_width: 
    :return: 
    """
    lane_data = {
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

    if lane_type == 'cycleway':
        bicycle_lane_location = get_bicycle_lane_location(p)
        lane_data['bicycle_forward_location'] = bicycle_lane_location['bicycle_forward_location']
        lane_data['bicycle_backward_location'] = bicycle_lane_location['bicycle_backward_location']

    for x in p['tags']:
        lane_data[x] = p['tags'][x]

    if lane_type == 'left':
        lane_data['lane_id'] = str(lane_id) + 'L'
    elif lane_type == 'right':
        lane_data['lane_id'] = str(lane_id) + 'R'

    if 'name' in p['tags']:
        name = p['tags']['name']
    elif 'highway' in p['tags'] and 'link' in p['tags']['highway']:
        name = p['tags']['highway']
    else:
        name = 'no_name'

    lane_data['name'] = name
    lane_data['nodes'] = p['nodes']
    lane_data['nodes_coordinates'] = [(nodes_dict[n]['x'], nodes_dict[n]['y']) for n in lane_data['nodes']]
    lane_data['right_shaped_border'] = None
    lane_data['left_shaped_border'] = None

    if right_border is None:
        lane_data['left_border'] = copy.deepcopy(left_border)
        lane_data['right_border'] = shift_list_of_nodes(left_border, [width]*len(left_border))
    elif left_border is None:
        lane_data['right_border'] = copy.deepcopy(right_border)
        lane_data['left_border'] = shift_list_of_nodes(right_border, [-width]*len(right_border))

        if 'L' in lane_data['lane_id']:
            right_border_with_inserted_points = add_incremental_points(right_border, n=shape_points, l=shape_length)
            delta_len = len(right_border_with_inserted_points) - len(right_border)
            shaped_widths = get_shaped_lane_width(-width, n=shape_points)
            width_list = shaped_widths[:delta_len] + [-width]*len(right_border)
            if lane_data['lane_id'] == '1L':
                lane_data['right_shaped_border'] = copy.deepcopy(lane_data['right_border'])
                lane_data['left_shaped_border'] = shift_list_of_nodes(right_border_with_inserted_points, width_list)
            elif right_shaped_border is not None:
                lane_data['right_shaped_border'] = copy.deepcopy(right_shaped_border)
                lane_data['left_shaped_border'] = shift_list_of_nodes(right_shaped_border, width_list,
                                                                      direction_reference=lane_data['right_border']
                                                                      )
    else:
        lane_data['right_border'] = copy.deepcopy(right_border)
        lane_data['left_border'] = copy.deepcopy(left_border)

    if 'L' not in lane_data['lane_id']:
        lane_data['right_shaped_border'] = None
        lane_data['left_shaped_border'] = None

    lane_data['median'] = shift_list_of_nodes(lane_data['left_border'], [width/2.0]*len(lane_data['left_border']))
    lane_data['length'] = get_border_length(lane_data['median'])
    insert_referenced_nodes(lane_data, nodes_dict)
    return lane_data


def add_lane(lane_data, merged_lane=None):
    """
    Add lane to a merged lane
    :param lane_data: lane dictionary
    :param merged_lane: lane dictionary
    :return: merged lane dictionary
    """
    if 'split' in lane_data:
        split = lane_data['path']['tags']['split']
    else:
        split = 'no'

    if merged_lane is None:
        merged_lane = {
            'width': [lane_data['width']],
            'path_id': [lane_data['path_id']],
            'path': [copy.deepcopy(lane_data['path'])],
            'nodes': copy.deepcopy(lane_data['nodes']),
            'left_border': copy.deepcopy(lane_data['left_border']),
            'median': copy.deepcopy(lane_data['median']),
            'right_border': copy.deepcopy(lane_data['right_border']),
            'nodes_coordinates': copy.deepcopy(lane_data['nodes_coordinates']),
            'right_shaped_border': copy.deepcopy(lane_data['right_shaped_border']),
            'left_shaped_border': copy.deepcopy(lane_data['left_shaped_border']),
            'shape_points': copy.deepcopy(lane_data['shape_points']),
            'shape_length': copy.deepcopy(lane_data['shape_length']),
            'split': [split],
        }
    else:

        split_transition = merged_lane['split'][-1] + '2' + split
        # split_transition options: yes2no, no2yes, yes2yes, no2no
        for k in ['left_border', 'right_border', 'median']:
            if split_transition == 'yes2no':
                merged_lane[k] = merged_lane[k][:-1] + lane_data[k][1:]
            elif split_transition == 'no2yes':
                merged_lane[k] = merged_lane[k][:-1] + lane_data[k][1:]
            else:
                merged_lane[k] += lane_data[k][1:]
        for k in ['nodes', 'nodes_coordinates']:
            merged_lane[k] += lane_data[k][1:]

        merged_lane['split'] += [split]

        for k in ['width', 'path_id', 'path']:
            merged_lane[k] += [lane_data[k]]

        if merged_lane['right_shaped_border'] is not None:
            merged_lane['right_shaped_border'] += lane_data['right_border']
        if merged_lane['left_shaped_border'] is not None:
            merged_lane['left_shaped_border'] += lane_data['left_border']

    for k in lane_data:
        if k not in ['width',
                     'path_id',
                     'path',
                     'nodes',
                     'left_border',
                     'right_border',
                     'median',
                     'nodes_coordinates',
                     'right_shaped_border',
                     'left_shaped_border',
                     'shape_length',
                     'shape_points',
                     'split']:
            merged_lane[k] = lane_data[k]

        merged_lane['length'] = get_border_length(merged_lane['median'])

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


def reshape_lane(lane_data, lanes):
    """
    Reapply starting shapes to a lane
    :param lane_data: dictionary
    :param lanes: list of dictionaries
    :return: None
    """
    if 'L' in lane_data['lane_id'] and '1L' not in lane_data['lane_id']:
        next_to_right = get_next_right_lane(lane_data, lanes)

        if next_to_right is not None and 'prev' in next_to_right and next_to_right['prev'] is not None:

            right_border_with_inserted_points = add_incremental_points(lane_data['right_border'],
                                                                       n=lane_data['shape_points'],
                                                                       l=lane_data['shape_length']
                                                                       )
            delta_len = len(right_border_with_inserted_points) - len(lane_data['right_border'])
            shaped_widths = get_shaped_lane_width(-lane_data['width'], n=lane_data['shape_points'])
            width_list = shaped_widths[:delta_len] + [-lane_data['width']] * len(lane_data['right_border'])
            lane_data['left_shaped_border'] = shift_list_of_nodes(right_border_with_inserted_points, width_list)
            lane_data['right_shaped_border'] = copy.deepcopy(lane_data['right_border'])


def reshape_lanes(lanes):
    """
    Reapply starting shapes to existing lanes
    :param lanes: list of dictionaries
    :return: None
    """
    for lane_data in lanes:
        reshape_lane(lane_data, lanes)


def extend_origin_left_border(lane_data, all_lanes):
    """
    Extend the last section of the left border to a large size in order to find cross points with other lanes
    :param lane_data: lane dictionary
    :param all_lanes: list of dictionaries
    :return: list of coordinates representing new extended border
    """

    shorten_lane_for_crosswalk(lane_data, all_lanes)

    return lane_data['left_shaped_border'][:-2] + extend_vector(lane_data['left_shaped_border'][-2:], backward=False)


def extend_destination_left_border(lane_data):
    """
    Extend the last section of the left border to a large size in order to find cross points with other lanes
    :param lane_data: destination lane
    :return: left border extended backwards
    """
    return extend_vector(lane_data['left_border'][:2]) + lane_data['left_border'][2:]


def intersects(origin_lane, destination_lane, all_lanes):
    """
    Check if two streets intersects.
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


def get_lanes(paths, nodes_dict, shape_points=16, shape_length=10.0, width=3.08):
    lanes = []
    for p in paths:
        lanes.extend(get_lanes_from_path(p,
                                         nodes_dict,
                                         shape_points=shape_points,
                                         shape_length=shape_length,
                                         width=width
                                         )
                     )

    return lanes


def get_bicycle_lanes(paths, nodes_dict, width=1.0):
    lanes = []
    for path_data in paths:
        lanes.extend(get_bicycle_lanes_from_path(path_data, nodes_dict, width=width))
    return lanes


def get_bicycle_lanes_from_path(path_data, nodes_dict, width=1.0):

    if len(path_data['nodes']) < 2:
        return []

    if key_value_check([('bicycle', 'no')], path_data):
        return []

    lanes = []

    if is_shared(path_data):
        lane_data = create_lane(path_data,
                                nodes_dict,
                                right_border=path_data['right_border'],
                                lane_id='1B',
                                lane_type='cycleway',
                                direction=path_data['tags']['direction'],
                                width=width
                                )
        lanes.append(lane_data)
    else:
        bicycle_lane_location = get_bicycle_lane_location(path_data)
        fl = bicycle_lane_location['bicycle_forward_location']
        bl = bicycle_lane_location['bicycle_backward_location']
        if fl == 'right' and bl == 'right':
            backward_lane_data = create_lane(path_data,
                                             nodes_dict,
                                             left_border=path_data['right_border'],
                                             lane_id='1B',
                                             lane_type='cycleway',
                                             direction=reverse_direction(path_data['tags']['direction']),
                                             width=width
                                             )
            forward_lane_data = create_lane(path_data,
                                            nodes_dict,
                                            left_border=backward_lane_data['right_border'],
                                            lane_id='1B',
                                            lane_type='cycleway',
                                            direction=path_data['tags']['direction'],
                                            width=width
                                            )
            lanes.append(forward_lane_data)
            lanes.append(backward_lane_data)

        elif fl == 'right' and bl == 'left':
            backward_lane_data = create_lane(path_data,
                                             nodes_dict,
                                             right_border=path_data['left_border'],
                                             lane_id='1B',
                                             lane_type='cycleway',
                                             direction=reverse_direction(path_data['tags']['direction']),
                                             width=width
                                             )
            forward_lane_data = create_lane(path_data,
                                            nodes_dict,
                                            left_border=path_data['right_border'],
                                            lane_id='1B',
                                            lane_type='cycleway',
                                            direction=path_data['tags']['direction'],
                                            width=width
                                            )
            lanes.append(forward_lane_data)
            lanes.append(backward_lane_data)

        elif fl == 'left' and bl == 'left':
            forward_lane_data = create_lane(path_data,
                                            nodes_dict,
                                            right_border=path_data['left_border'],
                                            lane_id='1B',
                                            lane_type='cycleway',
                                            direction=path_data['tags']['direction'],
                                            width=width
                                            )
            backward_lane_data = create_lane(path_data,
                                             nodes_dict,
                                             right_border=forward_lane_data['left_border'],
                                             lane_id='1B',
                                             lane_type='cycleway',
                                             direction=reverse_direction(path_data['tags']['direction']),
                                             width=width
                                             )
            lanes.append(forward_lane_data)
            lanes.append(backward_lane_data)

        elif fl == 'left' and bl == 'right':
            forward_lane_data = create_lane(path_data,
                                            nodes_dict,
                                            right_border=path_data['left_border'],
                                            lane_id='1B',
                                            lane_type='cycleway',
                                            direction=path_data['tags']['direction'],
                                            width=width
                                            )
            backward_lane_data = create_lane(path_data,
                                             nodes_dict,
                                             left_border=path_data['right_border'],
                                             lane_id='1B',
                                             lane_type='cycleway',
                                             direction=reverse_direction(path_data['tags']['direction']),
                                             width=width
                                             )
            lanes.append(forward_lane_data)
            lanes.append(backward_lane_data)

        elif fl == 'left' and bl is None:
            forward_lane_data = create_lane(path_data,
                                            nodes_dict,
                                            right_border=path_data['left_border'],
                                            lane_id='1B',
                                            lane_type='cycleway',
                                            direction=path_data['tags']['direction'],
                                            width=width
                                            )
            lanes.append(forward_lane_data)

        elif fl == 'right' and bl is None:
            forward_lane_data = create_lane(path_data,
                                            nodes_dict,
                                            left_border=path_data['right_border'],
                                            lane_id='1B',
                                            lane_type='cycleway',
                                            direction=path_data['tags']['direction'],
                                            width=width
                                            )
            lanes.append(forward_lane_data)

        elif fl is None and bl == 'right':
            backward_lane_data = create_lane(path_data,
                                             nodes_dict,
                                             left_border=path_data['right_border'],
                                             lane_id='1B',
                                             lane_type='cycleway',
                                             direction=reverse_direction(path_data['tags']['direction']),
                                             width=width
                                             )
            lanes.append(backward_lane_data)

        elif fl is None and bl == 'left':
            backward_lane_data = create_lane(path_data,
                                             nodes_dict,
                                             right_border=path_data['left_border'],
                                             lane_id='1B',
                                             lane_type='cycleway',
                                             direction=reverse_direction(path_data['tags']['direction']),
                                             width=width
                                             )
            lanes.append(backward_lane_data)

    return lanes


def get_bicycle_lane_width(bicycle_lane_location, location, bicycle_lane_width=1.0):
    """
    Calculate the combined width of bicycle lanes at the left or right side of the trunk lanes.
    This is needed to allow some space between the trunk and turn lanes to fit bicycle lanes.
    :param bicycle_lane_location: dictionary
    :param location: string: either right or left
    :param bicycle_lane_width: float in m
    :return: float in meters
    """
    w = 0.0
    if bicycle_lane_location['bicycle_forward_location'] == location:
        w += bicycle_lane_width
    if bicycle_lane_location['bicycle_backward_location'] == location:
        w += bicycle_lane_width
    return w


def get_lanes_from_path(path_data, nodes_dict, shape_points=16, shape_length=10.0, width=3.08, bicycle_lane_width=1.0):
    """
    Create a lane from a path
    :param path_data: dictionary
    :param nodes_dict: dictionary
    :param shape_points: integer number of points to create a shaped border of a turn lane
    :param shape_length: float in meters: the length of the shaped portion of the border
    :param width: float in meters
    :param bicycle_lane_width: float in meters
    :return: list of dictionaries
    """
    if len(path_data['nodes']) < 1:
        logger.warning("Path %d does not have enough nodes: %r" % (path_data['id'], path_data['nodes']))
        return []

    if path_data['left_border'] is None or len(path_data['left_border']) < 2:
        logger.warning("Path %d has an invalid left border: %r" % (path_data['id'], path_data['left_border']))
        return []

    if path_data['right_border'] is None or len(path_data['right_border']) < 2:
        logger.warning("Path %d has an invalid right border: %r" % (path_data['id'], path_data['right_border']))
        return []

    lanes = []

    num_of_lanes = get_num_of_lanes(path_data)

    if 'turn:lanes' in path_data['tags']:
        path_data['tags']['turn:lanes'] = path_data['tags']['turn:lanes'].replace('none', '').replace('None', '')
        lane_types = path_data['tags']['turn:lanes'].split('|')
    elif 'railway' in path_data['tags']:
        lane_types = ['rail_track'] * num_of_lanes
    else:
        lane_types = [''] * num_of_lanes

    lane_types = lane_types[::-1]

    num_of_left_lanes, num_of_right_lanes, num_of_trunk_lanes = count_lanes(path_data)
    bicycle_lane_location = get_bicycle_lane_location(path_data)

    # Construct trunk lanes
    left_border = copy.deepcopy(path_data['left_border'])
    for i in range(num_of_trunk_lanes, 0, -1):
        lane_type = lane_types[i + num_of_right_lanes - 1]
        lane_data = create_lane(path_data,
                                nodes_dict,
                                left_border=left_border,
                                lane_id=str(i),
                                lane_type=lane_type,
                                direction=path_data['tags']['direction'],
                                shape_points=shape_points, shape_length=shape_length,
                                num_of_left_lanes=num_of_left_lanes,
                                num_of_right_lanes=num_of_right_lanes,
                                num_of_trunk_lanes=num_of_trunk_lanes,
                                width=width
                                )
        lanes.append(lane_data)
        left_border = lane_data['right_border']

    space_for_bike_lane = get_bicycle_lane_width(bicycle_lane_location, 'right', bicycle_lane_width=bicycle_lane_width)
    if space_for_bike_lane > 0.0:
        space = create_lane(path_data,
                            nodes_dict,
                            left_border=left_border,
                            lane_id='1B',
                            lane_type='cycleway',
                            direction=path_data['tags']['direction'],
                            shape_points=shape_points, shape_length=shape_length,
                            num_of_left_lanes=num_of_left_lanes,
                            num_of_right_lanes=num_of_right_lanes,
                            num_of_trunk_lanes=num_of_trunk_lanes,
                            width=space_for_bike_lane
                            )
        left_border = space['right_border']

    # Construct right turn lanes
    for i in range(num_of_right_lanes, 0, -1):
        lane_data = create_lane(path_data,
                                nodes_dict,
                                left_border=left_border,
                                lane_id=str(i),
                                lane_type='right',
                                direction=path_data['tags']['direction'],
                                shape_points=shape_points, shape_length=shape_length,
                                num_of_left_lanes=num_of_left_lanes,
                                num_of_right_lanes=num_of_right_lanes,
                                num_of_trunk_lanes=num_of_trunk_lanes,
                                width=width
                                )
        lanes.append(lane_data)
        left_border = lane_data['right_border']

    right_border = copy.deepcopy(path_data['left_border'])
    right_shaped_border = right_border

    space_for_bike_lane = get_bicycle_lane_width(bicycle_lane_location, 'left', bicycle_lane_width=bicycle_lane_width)
    if space_for_bike_lane > 0.0:
        space = create_lane(path_data,
                            nodes_dict,
                            right_border=right_border,
                            lane_id='1B',
                            lane_type='cycleway',
                            direction=path_data['tags']['direction'],
                            right_shaped_border=right_shaped_border,
                            shape_points=shape_points, shape_length=shape_length,
                            num_of_left_lanes=num_of_left_lanes,
                            num_of_right_lanes=num_of_right_lanes,
                            num_of_trunk_lanes=num_of_trunk_lanes,
                            width=space_for_bike_lane
                            )
        right_border = space['left_border']
        right_shaped_border = space['left_shaped_border']

    # Construct left turn lanes
    for i in range(num_of_left_lanes):
        lane_data = create_lane(path_data,
                                nodes_dict,
                                right_border=right_border,
                                lane_id=str(i + 1),
                                lane_type='left',
                                direction=path_data['tags']['direction'],
                                right_shaped_border=right_shaped_border,
                                shape_points=shape_points, shape_length=shape_length,
                                num_of_left_lanes=num_of_left_lanes,
                                num_of_right_lanes=num_of_right_lanes,
                                num_of_trunk_lanes=num_of_trunk_lanes,
                                width=width
                                )
        lanes.append(lane_data)
        right_border = lane_data['left_border']
        right_shaped_border = lane_data['left_shaped_border']

    return lanes


def merge_lanes(lanes, nodes_dict):
    """
    Merge lanes for same street, direction, lane id
    :param lanes: list of dictionaries
    :param nodes_dict: dictionary of nodes
    :return: list of dictionaries
    """
    if lanes:
        lane_type = lanes[0]['lane_type']
        if lane_type == 'cycleway':
            lane_type = 'bicycle'
        elif lane_type == 'footway':
            lane_type = 'footway'
        elif lane_type == 'railway':
            lane_type = 'railway'
        else:
            lane_type = 'vehicle'

        logger.info('Start merging %d lanes of type %s' % (len(lanes), lane_type))
    else:
        return []

    merged_lanes = []
    set_ids(lanes)
    for lane in [l for l in lanes if l['name'] == 'no_name']:
        merged_lanes.append(add_lane(lane, merged_lane=None))

    names = sorted(set([l['name'] for l in lanes if l['name'] != 'no_name']))

    for name in names:
        ids = sorted(set([l['lane_id'] for l in lanes if l['name'] == name]))

        for lane_id in ids:
            directions = sorted(set([l['direction'] for l in lanes if l['lane_id'] == lane_id and l['name'] == name]))

            for direction in directions:
                similar_lanes = [l for l in lanes
                                 if l['lane_id'] == lane_id
                                 and l['name'] == name
                                 and l['direction'] == direction
                                 and len(l['nodes']) > 0
                                 ]

                for similar_lane in similar_lanes:
                    if not isinstance(similar_lane['path'],dict):
                        continue
                    bearing = similar_lane['path']['bearing']
                    next_lanes = [l for l in similar_lanes
                                  if isinstance(l['path'],dict)
                                  and similar_lane['nodes'][-1] == l['nodes'][0]
                                  and abs(get_angle_between_bearings(l['path']['bearing'], bearing)) < 60.0
                                  ]
                    if len(next_lanes) == 0:
                        similar_lane['next'] = None
                    else:
                        if next_lanes[0]['path_id'] != similar_lane['path_id']:
                            similar_lane['next'] = next_lanes[0]['path_id']
                        else:
                            similar_lane['next'] = None

                    prev_lanes = [l for l in similar_lanes
                                  if isinstance(l['path'],dict)
                                  and similar_lane['nodes'][0] == l['nodes'][-1]
                                  and abs(get_angle_between_bearings(l['path']['bearing'], bearing)) < 60.0
                                  ]
                    if len(prev_lanes) == 0:
                        similar_lane['prev'] = None
                    else:
                        if prev_lanes[0]['path_id'] != similar_lane['path_id']:
                            similar_lane['prev'] = prev_lanes[0]['path_id']
                        else:
                            similar_lane['prev'] = None

                for start_lane in [l for l in similar_lanes if "prev" in l and l['prev'] is None]:

                    merged_lane = add_lane(start_lane, merged_lane=None)

                    nxt = start_lane['next']

                    while nxt is not None:
                        next_lane = [l for l in similar_lanes if l['path_id'] == nxt][0]
                        merged_lane = add_lane(next_lane, merged_lane=merged_lane)
                        nxt = next_lane['next']

                    merged_lanes.append(merged_lane)

    set_lane_bearing(merged_lanes)
    add_node_tags_to_lanes(merged_lanes, nodes_dict)
    insert_referenced_nodes_to_lanes(merged_lanes, nodes_dict)
    logger.info('Total %d merged lanes' % len(merged_lanes))
    return merged_lanes


def set_ids(lanes):
    """
    Set ids for a list of lanes.  
    Lanes are numbered separately for each intersection starting from 1.
    :param lanes: list of dictionaries
    :return: None
    """
    for n, m in enumerate(lanes):
        m['id'] = n + 1


def add_value_to_dict(d, k, v):
    """
    Add a value to the dictionary.  If the value exists and not None, skip.
    :param d: dictionary
    :param k: key
    :param v: value
    :return: None
    """
    if k in ['x', 'y', 'osmid', 'street_name']:
        return
    if k not in d or d[k] is None:
        d[k] = v


def add_node_tags_to_lane(lane_data, nodes_dict):
    """
    Add node tags to the lane data.  
    Nodes will will be processed in the reverse order if the lane direction is from intersection,
    otherwise in the normal order.
    :param lane_data: dictionary
    :param nodes_dict: dictionary
    :return: None
    """
    if lane_data['direction'] == 'from_intersection':
        for node_id in lane_data['nodes'][::-1]:
            for k in nodes_dict[node_id]:
                add_value_to_dict(lane_data, k, nodes_dict[node_id][k])
    else:
        for node_id in lane_data['nodes']:
            for k in nodes_dict[node_id]:
                add_value_to_dict(lane_data, k, nodes_dict[node_id][k])


def add_node_tags_to_lanes(lanes, nodes_dict):
    """
    Add node tags to a list of lanes.  
    Nodes will will be processed in the reverse order if the lane direction is from intersection,
    otherwise in the normal order.
    :param lanes: list of dictionaries
    :param nodes_dict: dictionary
    :return: None
    """
    for lane_data in lanes:
        add_node_tags_to_lane(lane_data, nodes_dict)


def is_lane_crossing_another_street(lane_data, another_street, nodes_dict):
    """
    Check if the lane crosses another street, i.e. there is a common node.
    This is a more strict check than function intersect above
    :param lane_data: dictionary
    :param another_street: string
    :param nodes_dict: dictionary
    :return: True if crosses, False otherwise
    """
    for n in lane_data['nodes']:
        if n not in nodes_dict or 'street_name' not in nodes_dict[n]:
            continue
        if n in nodes_dict and another_street in nodes_dict[n]['street_name']:
            return True
    return False


def insert_referenced_nodes(lane_data, nodes_dict):
    """
    Insert data about each referenced node into the lane dictionary
    :param lane_data: dictionary
    :param nodes_dict: dictionary
    :return: None
    """
    lane_data['nodes_dict'] = {}
    for n in lane_data['nodes']:
        lane_data['nodes_dict'][n] = nodes_dict[n]


def insert_referenced_nodes_to_lanes(lanes, nodes_dict):
    """
    Insert data about each referenced node into each lane in the list
    :param lanes list of dictionaries
    :param nodes_dict: dictionary
    :return: None
    """

    for lane_data in lanes:
        insert_referenced_nodes(lane_data, nodes_dict)


def get_link_from_and_to(lane_data, lanes):
    """
    Get street names for a link connecting two streets
    :param lane_data: dictionary
    :param lanes: list of dictionaries
    :return: tuple of names (strings)
    """
    if 'highway' not in lane_data or 'link' not in lane_data['highway'] or len(lane_data['nodes']) == 0:
        return None, None

    from_name = ''
    for l in lanes:
        if 'no_name' not in l['name'] and lane_data['nodes'][0] in l['nodes']:
            from_name = l['name']
            break

    to_name = ''
    for l in lanes:
        if 'no_name' not in l['name'] and lane_data['nodes'][-1] in l['nodes']:
            to_name = l['name']
            break

    return from_name, to_name


def is_opposite_lane_exist(lane_data, lanes):
    """
    Check if an opposite traffic exists for the same street
    :param lane_data: lane dictionary
    :param lanes: list of lane dictionaries
    :return: True or False
    """
    if lane_data['direction'] == 'to_intersection':
        opposite_direction = 'from_intersection'
    else:
        opposite_direction = 'to_intersection'

    opposite_bearing = (lane_data['bearing'] + 180.0) % 360.0
    opposite_lanes = [l for l in lanes if l['name'] == lane_data['name']
                      and opposite_direction in l['direction']
                      and abs(get_angle_between_bearings(opposite_bearing, l['bearing'])) < 30
                      ]
    if opposite_lanes:
        return True
    else:
        return False


def insert_distance_to_center(x_data, lane_data):
    if "median" in lane_data:
        border = "median"
    elif "left_border" in lane_data:
        border = "left_border"
    else:
        border = None

    if border is not None:
        dist = get_distance_from_point_to_line((x_data['center_x'], x_data['center_y']),
                                           lane_data[border])
    else:
        dist = 0

    lane_data["distance_to_center"] = dist
    if "id" in lane_data:
        l_id = lane_data["id"]
    else:
        l_id = -1
    logger.debug("Lane %d distance %r from the intersection" % (l_id, dist))


def insert_distances(x_data, all_lanes):
    for l in all_lanes:
        insert_distance_to_center(x_data, l)
