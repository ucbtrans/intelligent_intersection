#!/usr/bin/env python
# -*- coding: utf-8 -*-

#######################################################################
#
#   This module support creation of guideways
#
#######################################################################


from border import get_bicycle_border
from matplotlib.patches import Polygon
from right_turn import get_right_turn_border, get_link, get_link_destination_lane, is_right_turn_allowed, \
    get_destination_lanes_for_right_turn
from left_turn import is_left_turn_allowed, get_destination_lanes_for_left_turn
from through import is_through_allowed, get_destination_lane
from u_turn import is_u_turn_allowed, get_destination_lanes_for_u_turn, get_u_turn_border
from turn import get_turn_border
from log import get_logger, dictionary_to_log


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
        if is_left_turn_allowed(origin_lane):
            for destination_lane in get_destination_lanes_for_left_turn(origin_lane, all_lanes, nodes_dict):
                origin_candidates = [g for g in through_guideways if g['origin_lane']['id'] == origin_lane['id']]
                destination_candidates = [g for g in through_guideways
                                          if g['destination_lane']['id'] == destination_lane['id']
                                          ]
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
        'left_border':  get_bicycle_border(origin_through['left_border'], destination_through['left_border']),
        'median':       get_bicycle_border(origin_through['median'], destination_through['median']),
        'right_border': get_bicycle_border(origin_through['right_border'], destination_through['right_border'])
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
            for destination_lane in get_destination_lanes_for_left_turn(origin_lane, all_lanes, nodes_dict):
                logger.debug('Destin Lane ' + dictionary_to_log(destination_lane))
                try:
                    guideway_data = get_direct_turn_guideway(origin_lane, destination_lane, all_lanes, turn_type='left')
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

    guideway = {
        'direction': 'right',
        'origin_lane': origin_lane,
    }

    link_lane = get_link(origin_lane, all_lanes)
    if link_lane is None:
        destination_lanes = get_destination_lanes_for_right_turn(origin_lane, all_lanes)
        if len(destination_lanes) > 0:
            return get_direct_turn_guideway(origin_lane, destination_lanes[0], all_lanes, turn_type='right')
        else:
            return None

    guideway['link_lane'] = link_lane

    destination_lane = get_link_destination_lane(link_lane, all_lanes)
    if destination_lane is None:
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
    if guideway['left_border'] is None or guideway['right_border'] is None:
        return None

    return guideway


def get_through_guideway(origin_lane, destination_lane):
    """
    Create a through guideway from an origin and destination lanes
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :return: dictionary
    """
    return {
        'direction': 'through',
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
        'left_border': origin_lane['left_border'][:-1] + destination_lane['left_border'][1:],
        'median': origin_lane['left_border'][:-1] + destination_lane['median'][1:],
        'right_border': origin_lane['right_border'][:-1] + destination_lane['right_border'][1:]
    }


def get_u_turn_guideways(all_lanes):
    """
    Compile a list of bicycle guideways for all legal u-turns
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """

    logger.info('Starting U-turn guideways')
    guideways = []

    for origin_lane in all_lanes:
        if is_u_turn_allowed(origin_lane):
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


def get_direct_turn_guideway(origin_lane, destination_lane, all_lanes, turn_type='right'):
    """
    Create a right or left turn guideway if there is no link lane connecting origin and destination
    :param origin_lane: dictionary
    :param destination_lane: dictionary
    :param all_lanes: list of dictionaries
    :param turn_type: string: 'right' for a right turn, left' a for left one
    :return: dictionary
    """

    if turn_type == 'right':
        if not is_right_turn_allowed(origin_lane, all_lanes):
            return None
        turn_direction = 1
    else:
        if not is_left_turn_allowed(origin_lane):
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
        return None

    right_border = get_turn_border(origin_lane,
                                   destination_lane,
                                   all_lanes,
                                   border_type='right',
                                   turn_direction=turn_direction
                                   )
    if right_border is None:
        return None

    median = get_turn_border(origin_lane,
                             destination_lane,
                             all_lanes,
                             border_type='median',
                             turn_direction=turn_direction
                             )
    if median is None:
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
    Set guideway types based on the origin lane type
    :param guideways: list of dictionaries
    :return: list of dictionaries
    """

    for g in guideways:
        set_guideway_id(g)

    return guideways


def set_guideway_id(g):
    """
    Set guideway id as a combination of the origin and destination ids.
    Set guideway types based on the origin lane type
    :param g: guideway dictionary
    :return: None
    """

    if g is not None:
        g['id'] = 100*g['origin_lane']['id'] + g['destination_lane']['id']
        if g['origin_lane']['lane_type'] == 'cycleway':
            g['type'] = 'bicycle'
        elif 'rail' in g['origin_lane']['lane_type']:
            g['type'] = 'railway'
        elif g['origin_lane']['lane_type'] == 'crosswalk':
            g['type'] = 'footway'
        else:
            g['type'] = 'drive'


def get_polygon_from_guideway(guideway, fc='y', ec='w', alpha=0.8, linestyle='dashed', joinstyle='round'):
    """
    Get a polygon from a guideway
    """

    polygon_sequence = guideway['left_border'] + guideway['right_border'][::-1]

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
        if guideway_data['destination_lane']['lane_type'] == 'cycleway':
            fcolor = '#00FF00'
            ecolor = '#00FF00'
        else:
            fcolor = fc
            ecolor = ec
        ax.add_patch(get_polygon_from_guideway(guideway_data, alpha=alpha, fc=fcolor, ec=ecolor))

    return fig, ax
