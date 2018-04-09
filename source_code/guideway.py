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


def get_bicycle_left_turn_guideways(all_lanes, nodes_dict):
    """
    Compile a list of bicycle guideways for all legal left turns
    :param all_lanes: list of dictionaries
    :param nodes_dict: dictionary
    :return: list of dictionaries
    """

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
                    guideway_data = get_bicycle_left_guideway(origin_lane,
                                                              destination_lane,
                                                              origin_candidates[0],
                                                              destination_candidates[0]
                                                              )
                else:
                    guideway_data = None

                if guideway_data is not None \
                        and guideway_data['left_border'] is not None \
                        and guideway_data['right_border'] is not None:
                    guideways.append(guideway_data)

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
        'type': 'left',
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
        'left_border': get_bicycle_border(origin_through['left_border'], destination_through['left_border']),
        'right_border': get_bicycle_border(origin_through['right_border'], destination_through['right_border'])
    }


def get_left_turn_guideways(all_lanes, nodes_dict):
    """
    Compile a list of guideways for all legal left turns
    :param all_lanes: list of dictionaries
    :param nodes_dict: dictionary
    :return: list of dictionaries
    """

    guideways = []
    for origin_lane in all_lanes:
        if is_left_turn_allowed(origin_lane):
            for destination_lane in get_destination_lanes_for_left_turn(origin_lane, all_lanes, nodes_dict):
                guideway_data = get_direct_turn_guideway(origin_lane, destination_lane, all_lanes, turn_type='left')

                if guideway_data is not None:
                    guideways.append(guideway_data)
    return guideways


def create_right_turn_guideway(origin_lane, all_lanes):
    """
    Calculate the right border and create a guideway
    :param origin_lane: dictionary
    :param all_lanes: list of dictionary
    :return: dictionary
    """

    guideway = {
        'type': 'right',
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
        'type': 'through',
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
        'left_border': origin_lane['left_border'][:-1] + destination_lane['left_border'][1:],
        'right_border': origin_lane['right_border'][:-1] + destination_lane['right_border'][1:]
    }


def get_u_turn_guideways(all_lanes):
    """
    Compile a list of bicycle guideways for all legal u-turns
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """

    guideways = []

    for origin_lane in all_lanes:
        if is_u_turn_allowed(origin_lane):
            for destination_lane in get_destination_lanes_for_u_turn(origin_lane, all_lanes):
                guideway_data = get_u_turn_guideway(origin_lane, destination_lane, all_lanes)
                if guideway_data is not None \
                        and guideway_data['left_border'] is not None \
                        and guideway_data['right_border'] is not None:
                    guideways.append(guideway_data)

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
        'type': 'u_turn',
        'origin_lane': origin_lane,
        'destination_lane': destination_lane,
        'left_border': get_u_turn_border(origin_lane, destination_lane, all_lanes, 'left'),
        'right_border': get_u_turn_border(origin_lane, destination_lane, all_lanes, 'right')
    }


def get_through_guideways(all_lanes):
    """
    Create through guideways from a list of merged lanes
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """
    guideways = []
    for origin_lane in all_lanes:
        if is_through_allowed(origin_lane):
            destination_lane = get_destination_lane(origin_lane, all_lanes)
            if destination_lane is not None:
                guideways.append(get_through_guideway(origin_lane, destination_lane))
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
        'type': turn_type,
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

    guideway['left_border'] = left_border
    guideway['right_border'] = right_border
    return guideway


def get_right_turn_guideways(all_lanes):
    """
    Create a list of right turn guideways for lanes having an additional link to the destination
    :param all_lanes: list of dictionaries
    :return: list of dictionaries
    """
    guideways = [create_right_turn_guideway(l, all_lanes) for l in all_lanes if is_right_turn_allowed(l, all_lanes)]
    return [g for g in guideways if g is not None]


def set_guideway_ids(guideways):
    """
    Set guideway ids as a combination of the origin and destination ids
    :param guideways: list of dictionaries
    :return: list of dictionaries
    """
    for g in guideways:
        g['id'] = 100*g['origin_lane']['id'] + g['destination_lane']['id']

    return guideways


def get_polygon_from_guideway(guideway, fc='y', ec='w', alpha=0.8, linestyle='dashed', joinstyle='round'):
    """
    Get a polygon from a lane
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
