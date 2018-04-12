#######################################################################
#
#   This module provides functions for public transit
#
#######################################################################


from border import get_closest_point, get_distance_between_points
from lane import get_lane_index_from_right
from node import get_node


def get_public_transit_stop(lane_data, stops, max_distance=20.0):
    """
    Get a list of public transit stops within the specified distance to the right border of a lane.
    Stop is a node.
    :param lane_data: dictionary
    :param stops: list of dictionaries
    :param max_distance: float in meters
    :return: list of stops (dictionaries)
    """
    nearby_stops = set()

    if 'right_border' not in lane_data:
        return []

    for stop in stops:
        s = get_node(stop)
        stop_location = (s['x'], s['y'])
        closest_point_on_the_border = get_closest_point(stop_location, lane_data['right_border'])
        distance = get_distance_between_points(stop_location, closest_point_on_the_border)
        if distance < max_distance:
            nearby_stops.add(stop['id'])

    return [s for s in stops if s['id'] in nearby_stops]
