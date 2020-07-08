#!/usr/bin/env python
# -*- coding: utf-8 -*-

#######################################################################
#
#   This module support creation of guideways
#
#######################################################################


import copy
from border import get_bicycle_border, cut_line_by_relative_distance, cut_border_by_point, \
    get_border_length
from matplotlib.patches import Polygon
from right_turn import get_right_turn_border, get_link, get_link_destination_lane, \
    is_right_turn_allowed, \
    get_destination_lanes_for_right_turn
from left_turn import is_left_turn_allowed, get_destination_lanes_for_left_turn
from through import is_through_allowed, get_destination_lane
from u_turn import is_u_turn_allowed, get_destination_lanes_for_u_turn, get_u_turn_border
from turn import get_turn_border
from log import get_logger, dictionary_to_log
from footway import crosswalk_intersects_median, get_crosswalk_to_crosswalk_distance

logger = get_logger()


def get_bicycle_left_turn_guideways(all_lanes, nodes_dict):
    """
    Compile a list of bicycle guideways for all legal left turns
    :param all_lanes: list of dictionaries
    :param nodes_dict: dictionary
    :return: list of dictionaries
    """
    logger.info('Starting bicycle left turn guideways')
    guideways = []
    through_guideways = get_through_guideways(all_lanes)

    for origin_lane in all_lanes:
        logger.debug("Allowed %r: %s %s %s" % (is_left_turn_allowed(origin_lane),
                                               origin_lane["lane_type"],
                                               origin_lane["direction"],
                                               origin_lane["name"]
                                               )
                     )

        # ll = [(l["name"], l["direction"]) for l in get_destination_lanes_for_left_turn(origin_lane, all_lanes, nodes_dict) ]
        # logger.debug("%r" % ll)

        if is_left_turn_allowed(origin_lane):
            for destination_lane in get_destination_lanes_for_left_turn(origin_lane, all_lanes,
                                                                        nodes_dict):
                origin_candidates = [g for g in through_guideways if
                                     g['origin_lane']['id'] == origin_lane['id']]
                destination_candidates = [g for g in through_guideways
                                          if g['destination_lane']['id'] == destination_lane['id']
                                          ]
                logger.debug('Number of candidates: origin %d, destination %d' % (
                    len(origin_candidates), len(destination_candidates)))
                if origin_candidates and destination_candidates:
                    logger.debug('Origin Lane ' + dictionary_to_log(origin_candidates[0]))
                    logger.debug('Destin Lane ' + dictionary_to_log(destination_candidates[0]))
                    try:
                        guideway_data = get_bicycle_left_guideway(origin_lane,
                                                                  destination_lane,
                                                                  origin_candidates[0],
                                                                  destination_candidates[0]
                                                                  )
                        set_guideway_id(guideway_data)
                    except Exception as e:
                        logger.exception(e)
                        guideway_data = None

                else:
                    guideway_data = None

                if guideway_data is not None \
                        and guideway_data['left_border'] is not None \
                        and guideway_data['median'] is not None \
                        and guideway_data['right_border'] is not None:
                    logger.debug('Guideway ' + dictionary_to_log(guideway_data))
                    guideways.append(guideway_data)

    logger.info('Created %d guideways' % len(guideways))
    return guideways


def get_bicycle_left_guideway(origin_lane, destination_lane, origin_through, destination_through):
    """
    Get a bicycle guideway for the left turn assuming that the bicyclist making the left turn as pedestrian, 
    i.e. as an instant 90 degree turn. Creating the bicycle guideway from an origin and destination lanes 
    and previously calculated through guideways.  
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param origin_through: dictionary
    :param destination_through: dictionary
    :return: dictionary
    """
    return {
        'direction': 'left',
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
        'left_border': get_bicycle_border(origin_through['left_border'],
                                          destination_through['left_border']),
        'median': get_bicycle_border(origin_through['median'], destination_through['median']),
        'right_border': get_bicycle_border(origin_through['right_border'],
                                           destination_through['right_border'])
    }


def get_left_turn_guideways(all_lanes, nodes_dict):
    """
    Compile a list of guideways for all legal left turns
    :param all_lanes: list of dictionaries
    :param nodes_dict: dictionary
    :return: list of dictionaries
    """
    logger.info('Starting left turn guideways')
    guideways = []
    for origin_lane in all_lanes:
        if is_left_turn_allowed(origin_lane):
            logger.debug('Origin Lane ' + dictionary_to_log(origin_lane))
            for destination_lane in get_destination_lanes_for_left_turn(origin_lane, all_lanes,
                                                                        nodes_dict):
                logger.debug('Destin Lane ' + dictionary_to_log(destination_lane))
                try:
                    guideway_data = get_direct_turn_guideway(origin_lane, destination_lane,
                                                             all_lanes, turn_type='left')
                    set_guideway_id(guideway_data)
                except Exception as e:
                    logger.exception(e)
                    guideway_data = None

                if guideway_data is not None:
                    logger.debug('Guideway ' + dictionary_to_log(guideway_data))
                    guideways.append(guideway_data)

    logger.info('Created %d guideways' % len(guideways))
    return guideways


def create_right_turn_guideway(origin_lane, all_lanes):
    """
    Calculate the right border and create a guideway
    :param origin_lane: dictionary
    :param all_lanes: list of dictionary
    :return: dictionary
    """
    logger.info('Starting right turn guideway')
    guideway = {
        'direction': 'right',
        'origin_lane': origin_lane,
    }

    link_lane = get_link(origin_lane, all_lanes)
    if link_lane is None:
        destination_lanes = get_destination_lanes_for_right_turn(origin_lane, all_lanes)
        if len(destination_lanes) > 0:
            return get_direct_turn_guideway(origin_lane, destination_lanes[0], all_lanes,
                                            turn_type='right')
        else:
            return None

    guideway['link_lane'] = link_lane

    destination_lane = get_link_destination_lane(link_lane, all_lanes)
    if destination_lane is None:
        logger.debug('Link destination not found. Origin id %d' % origin_lane['id'])
        return None

    if origin_lane['left_shaped_border'] is None:
        left_border_type = 'left_border'
    else:
        left_border_type = 'left_shaped_border'
    if origin_lane['right_shaped_border'] is None:
        right_border_type = 'right_border'
    else:
        right_border_type = 'right_shaped_border'

    guideway['destination_lane'] = destination_lane
    guideway['left_border'] = get_right_turn_border(origin_lane[left_border_type],
                                                    link_lane['left_border'],
                                                    destination_lane['left_border']
                                                    )
    guideway['median'] = get_right_turn_border(origin_lane['median'],
                                               link_lane['median'],
                                               destination_lane['median']
                                               )
    guideway['right_border'] = get_right_turn_border(origin_lane[right_border_type],
                                                     link_lane['right_border'],
                                                     destination_lane['right_border']
                                                     )
    if guideway['left_border'] is None:
        logger.debug(
            'Left border for the linked right turn is None. Origin id %d' % origin_lane['id'])
        return None
    if guideway['right_border'] is None:
        logger.debug(
            'Right border for the linked right turn is None. Origin id %d' % origin_lane['id'])
        return None

    return guideway


def get_through_guideway(origin_lane, destination_lane):
    """
    Create a through guideway from an origin and destination lanes
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :return: dictionary
    """
    logger.info('Starting through guideway')
    if origin_lane['nodes'][-1] == destination_lane['nodes'][0]:
        return {
            'direction': 'through',
            'origin_lane': origin_lane,
            'destination_lane': destination_lane,
            'left_border': origin_lane['left_border'] + destination_lane['left_border'][1:],
            'median': origin_lane['median'] + destination_lane['median'][1:],
            'right_border': origin_lane['right_border'] + destination_lane['right_border'][1:]
        }
    else:
        return {
            'direction': 'through',
            'origin_lane': origin_lane,
            'destination_lane': destination_lane,
            'left_border': origin_lane['left_border'][:-1] + destination_lane['left_border'][1:],
            'median': origin_lane['median'][:-1] + destination_lane['median'][1:],
            'right_border': origin_lane['right_border'][:-1] + destination_lane['right_border'][1:]
        }


def get_u_turn_guideways(all_lanes, x_data):
    """
    Compile a list of bicycle guideways for all legal u-turns
    :param all_lanes: list of dictionaries
    :param x_data: intersection dictionary
    :return: list of dictionaries
    """

    logger.info('Starting U-turn guideways')
    guideways = []

    for origin_lane in all_lanes:
        if is_u_turn_allowed(origin_lane, x_data):
            logger.debug('Origin Lane ' + dictionary_to_log(origin_lane))
            for destination_lane in get_destination_lanes_for_u_turn(origin_lane, all_lanes):
                logger.debug('Destin Lane ' + dictionary_to_log(destination_lane))
                try:
                    guideway_data = get_u_turn_guideway(origin_lane, destination_lane, all_lanes)
                    set_guideway_id(guideway_data)
                except Exception as e:
                    logger.exception(e)
                    guideway_data = None

                if guideway_data is not None \
                        and guideway_data['left_border'] is not None \
                        and guideway_data['median'] is not None \
                        and guideway_data['right_border'] is not None:
                    logger.debug('Guideway ' + dictionary_to_log(guideway_data))
                    guideways.append(guideway_data)

    logger.info('Created %d guideways' % len(guideways))
    return guideways


def get_u_turn_guideway(origin_lane, destination_lane, all_lanes):
    """
    Create a u-turn guideway from an origin and destination lanes
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :return: dictionary
    """
    return {
        'direction': 'u_turn',
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
        'left_border': get_u_turn_border(origin_lane, destination_lane, all_lanes, 'left'),
        'median': get_u_turn_border(origin_lane, destination_lane, all_lanes, 'median'),
        'right_border': get_u_turn_border(origin_lane, destination_lane, all_lanes, 'right')
    }


def get_through_guideways(all_lanes):
    """
    Create through guideways from a list of merged lanes
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """

    logger.info('Starting through guideways')
    guideways = []
    for origin_lane in all_lanes:
        if is_through_allowed(origin_lane):
            logger.debug('Origin Lane ' + dictionary_to_log(origin_lane))
            destination_lane = get_destination_lane(origin_lane, all_lanes)
            if destination_lane is not None:
                logger.debug('Destin Lane ' + dictionary_to_log(destination_lane))
                try:
                    guideway_data = get_through_guideway(origin_lane, destination_lane)
                    set_guideway_id(guideway_data)
                    guideways.append(guideway_data)
                    logger.debug('Guideway ' + dictionary_to_log(guideway_data))
                except Exception as e:
                    logger.exception(e)

    logger.info('Created %d guideways' % len(guideways))
    return guideways


def get_crosswalk_to_crosswalk_distance_along_guideway(guideway_data, crosswalks,
                                                       max_distance=50.0):
    """
    Calculate max distance between crosswalks along a guideway
    :param guideway_data: guideway dictionary
    :param crosswalks: list of crosswalks dictionaries
    :return: float in meters
    """
    nearest_crosswalks = [c for c in crosswalks if
                          "distance_to_center" not in c or c["distance_to_center"] < max_distance]
    origin_crosswalks = [c for c in nearest_crosswalks
                         if (c['simulated'] == 'no' or c['name'] == guideway_data['origin_lane'][
            'name'])
                         and crosswalk_intersects_median(c, guideway_data['origin_lane']['median'])
                         ]
    destination_crosswalks = [c for c in nearest_crosswalks
                              if (c['simulated'] == 'no' or c['name'] ==
                                  guideway_data['destination_lane']['name'])
                              and crosswalk_intersects_median(c, guideway_data['destination_lane'][
            'median'])
                              ]

    if len(origin_crosswalks) == 0:
        logger.warning('Unable to find origin crosswalks for %s guideway %d %s'
                       % (guideway_data['direction'], guideway_data['id'],
                          guideway_data['origin_lane']['name'])
                       )
        return -3
    if len(destination_crosswalks) == 0:
        logger.warning('Unable to find destination crosswalks for %s guideway %d %s'
                       % (guideway_data['direction'], guideway_data['id'],
                          guideway_data['destination_lane']['name'])
                       )
        return -4

    return max([get_crosswalk_to_crosswalk_distance(c1, c2, guideway_data['median'])
                for c1 in origin_crosswalks
                for c2 in destination_crosswalks
                ]
               )


def get_direct_turn_guideway(origin_lane, destination_lane, all_lanes, turn_type='right'):
    """
    Create a right or left turn guideway if there is no link lane connecting origin and destination
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :param turn_type: string: 'right' for a right turn, left' a for left one
    :return: dictionary
    """

    logger.debug('Starting direct turn guideway')
    if turn_type == 'right':
        if not is_right_turn_allowed(origin_lane, all_lanes):
            logger.debug('Right turn not allowed. Origin id %d' % origin_lane['id'])
            return None
        turn_direction = 1
    else:
        if not is_left_turn_allowed(origin_lane):
            logger.debug('Left turn not allowed. Origin id %d' % origin_lane['id'])
            return None
        turn_direction = -1

    guideway = {
        'direction': turn_type,
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
    }

    left_border = get_turn_border(origin_lane,
                                  destination_lane,
                                  all_lanes,
                                  border_type='left',
                                  turn_direction=turn_direction
                                  )
    if left_border is None:
        logger.debug('Left border failed. Origin id %d, Dest id %d' % (
            origin_lane['id'], destination_lane['id']))
        return None

    right_border = get_turn_border(origin_lane,
                                   destination_lane,
                                   all_lanes,
                                   border_type='right',
                                   turn_direction=turn_direction
                                   )
    if right_border is None:
        logger.debug('Right border failed. Origin id %d, Dest id %d' % (
            origin_lane['id'], destination_lane['id']))
        return None

    median = get_turn_border(origin_lane,
                             destination_lane,
                             all_lanes,
                             border_type='median',
                             turn_direction=turn_direction
                             )
    if median is None:
        logger.debug(
            'Median failed. Origin id %d, Dest id %d' % (origin_lane['id'], destination_lane['id']))
        return None

    guideway['left_border'] = left_border
    guideway['median'] = median
    guideway['right_border'] = right_border
    return guideway


def get_right_turn_guideways(all_lanes):
    """
    Create a list of right turn guideways for lanes having an additional link to the destination
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """

    logger.info('Starting right guideways')
    guideways = []
    for origin_lane in all_lanes:
        if is_right_turn_allowed(origin_lane, all_lanes):
            logger.debug('Origin Lane ' + dictionary_to_log(origin_lane))
            try:
                guideway_data = create_right_turn_guideway(origin_lane, all_lanes)
                set_guideway_id(guideway_data)
            except Exception as e:
                logger.exception(e)
                guideway_data = None

            if guideway_data is not None:
                logger.debug('Guideway ' + dictionary_to_log(guideway_data))
                guideways.append(guideway_data)

    logger.info('Created %d guideways' % len(guideways))
    return guideways


def set_guideway_ids(guideways):
    """
    Set guideway ids as a combination of the origin and destination ids.
    This function also sets guideway length.
    Set guideway types based on the origin lane type
    :param guideways: list of dictionaries
    :return: list of dictionaries
    """

    for g in guideways:
        set_guideway_length(g)
        set_guideway_id(g)

    return guideways


def set_guideway_length(g):
    """
    Set guideway length as the length of its median
    :param g: guideway dictionary
    :return: None
    """
    if g is None:
        logger.error('Guideway is None')
    else:
        g['length'] = get_border_length(g['median'])
        logger.debug('Guideway id %d length %r' % (g['id'], g['length']))


def set_guideway_id(g):
    """
    Set guideway id as a combination of the origin and destination ids.
    Set guideway types based on the origin lane type.
    This function also sets guideway length.
    :param g: guideway dictionary
    :return: None
    """

    if g is not None:
        g['id'] = 100 * g['origin_lane']['id'] + g['destination_lane']['id']
        if g['origin_lane']['lane_type'] == 'cycleway':
            g['type'] = 'bicycle'
        elif 'rail' in g['origin_lane']['lane_type']:
            g['type'] = 'railway'
        elif g['origin_lane']['lane_type'] == 'crosswalk':
            g['type'] = 'footway'
        else:
            g['type'] = 'drive'
        set_guideway_length(g)


def get_polygon_from_guideway(guideway_data,
                              fc='y',
                              ec='w',
                              alpha=0.8,
                              linestyle='dashed',
                              joinstyle='round',
                              reduced=False
                              ):
    """
    Get a polygon from a guideway
    """

    if reduced:
        polygon_sequence = guideway_data['reduced_left_border'] + guideway_data[
                                                                      'reduced_right_border'][::-1]
    else:
        polygon_sequence = guideway_data['left_border'] + guideway_data['right_border'][::-1]

    return Polygon(polygon_sequence,
                   closed=True,
                   fc=fc,
                   ec=ec,
                   alpha=alpha,
                   linestyle=linestyle,
                   joinstyle=joinstyle
                   )


def plot_guideways(guideways, fig=None, ax=None, cropped_intersection=None,
                   fig_height=15,
                   fig_width=15,
                   axis_off=False,
                   edge_linewidth=1,
                   margin=0.02,
                   bgcolor='#CCFFE5',
                   edge_color='#FF9933',
                   alpha=1.0,
                   fc='y',
                   ec='w'
                   ):
    """
    Plot lanes for existing street plot
    :param guideways:
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
    :return:
    """

    if fig is None or ax is None:
        if cropped_intersection is None:
            return None, None
        return None, None

    for guideway_data in guideways:
        if 'destination_lane' in guideway_data and guideway_data['destination_lane'][
            'lane_type'] == 'cycleway':
            fcolor = '#00FF00'
            ecolor = '#00FF00'
        else:
            fcolor = fc
            ecolor = ec
        ax.add_patch(get_polygon_from_guideway(guideway_data, alpha=alpha, fc=fcolor, ec=ecolor))

    return fig, ax


def relative_cut(guideway_data, relative_distance, starting_point="b"):
    """
    Reduce guideway by relative distance from either end.  The distance is in the range [0;1].
    The starting point can be either 'b' or 'e';  The guideway left and right borders and median will truncated.
    For example, if relative_distance = 0.3 and starting_point_for_cut="b", 
    then the function returns 30% of the original length starting from the beginning of the guideway.
    If relative_distance = 0.3 and starting_point_for_cut="e", 
    then the function returns 30% of the original length adjacent to the end of the guideway.
    In addition this function sets the new guideway length.  The origin and destination lane lengths are preserved 
    in the lane meta data sections.
    :param guideway_data: guideway dictionary
    :param relative_distance: relative length
    :param starting_point: string, either 'b' or 'e'
    :return: guideway dictionary with reduced borders and median
    """

    if guideway_data is None:
        return None

    cut_guideway = copy.deepcopy(guideway_data)
    if 'cut_history' in cut_guideway:
        cut_guideway['cut_history'].append(str(relative_distance) + '_' + starting_point)
    else:
        cut_guideway['cut_history'] = [str(relative_distance) + '_' + starting_point]

    if starting_point == "b":
        median = guideway_data['median']
        left_border = guideway_data['left_border']
        right_border = guideway_data['right_border']
    else:
        median = guideway_data['median'][::-1]
        left_border = guideway_data['left_border'][::-1]
        right_border = guideway_data['right_border'][::-1]

    cut_median = cut_line_by_relative_distance(median, relative_distance)
    cut_left_border = cut_border_by_point(left_border, cut_median[-1])
    cut_right_border = cut_border_by_point(right_border, cut_median[-1])

    if starting_point == "b":
        cut_guideway['median'] = cut_median
        cut_guideway['left_border'] = cut_left_border
        cut_guideway['right_border'] = cut_right_border
    else:
        cut_guideway['median'] = cut_median[::-1]
        cut_guideway['left_border'] = cut_left_border[::-1]
        cut_guideway['right_border'] = cut_right_border[::-1]

    set_guideway_length(cut_guideway)
    return cut_guideway
