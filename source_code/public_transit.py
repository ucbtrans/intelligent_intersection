#######################################################################
#
#   This module provides functions for public transit
#
#######################################################################


from border import get_distance_between_nodes


def get_public_transit_stop(lane_data, stops, nodes_dict, max_distance=20.0):

    nearby_stops = []
    for s in stops:
        for n in lane_data['nodes']:
            distance = get_distance_between_nodes(nodes_dict, s['id'], n)
            if distance < max_distance:
                nearby_stops.append(s)
    return nearby_stops
