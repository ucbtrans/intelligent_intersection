#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module creates lane borders
#
#######################################################################

import osmnx as ox
import math
import shapely.geometry as geom


rhumbs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']


def get_distance_between_nodes(nodes_d, id1, id2):
    return ox.great_circle_vec(nodes_d[id1]['y'], nodes_d[id1]['x'], nodes_d[id2]['y'], nodes_d[id2]['x'])


def shift_vector(node_coordinates, width, direction_reference=None):
    """
    Parallel shift a vector to the distance of width
    :param node_coordinates: list of coordinates
    :param width: distance to shift
    :param direction_reference: reference vector used to define shift direction
    :return: shifted list of coordinates
    """
    if len(node_coordinates) < 2:
        return node_coordinates

    x0 = node_coordinates[0][0]
    y0 = node_coordinates[0][1]
    x1 = node_coordinates[1][0]
    y1 = node_coordinates[1][1]

    if direction_reference is not None:
        vec = (direction_reference[1][0] - direction_reference[0][0],
               direction_reference[1][1] - direction_reference[0][1])
    else:
        vec = (x1 - x0, y1 - y0)

    norm = (vec[1], -vec[0])
    if ox.great_circle_vec(y0, x0, y0 + norm[1], x0 + norm[0]) > 0.1:
        scale = width / ox.great_circle_vec(y0, x0, y0 + norm[1], x0 + norm[0])
    else:
        scale = 0.0
    xx0 = x0 + norm[0] * scale
    yy0 = y0 + norm[1] * scale
    xx1 = x1 + norm[0] * scale
    yy1 = y1 + norm[1] * scale
    return [(xx0, yy0), (xx1, yy1)]


def extend_vector(coord, length=300.0, backward=True):
    """
    Extend (or reduce) the length of a vector to the required length
    :param coord: list of vector coord.
    :param length: desired length
    :param backward: True if extend backward, false if forward
    :return: list of coordinates for the new vector
    """
    if len(coord) < 2:
        return coord

    x0 = coord[0][0]
    y0 = coord[0][1]
    x1 = coord[1][0]
    y1 = coord[1][1]
    current_distance = ox.great_circle_vec(y0, x0, y1, x1)
    if current_distance < 0.01:
        return coord
    scale = length/current_distance
    if backward:
        xx0 = x1 - (x1 - x0) * scale
        yy0 = y1 - (y1 - y0) * scale
        return [(xx0, yy0), (x1, y1)]
    else:
        xx1 = x0 + (x1 - x0)*scale
        yy1 = y0 + (y1 - y0)*scale
        return [(x0, y0), (xx1, yy1)]


def extend_origin_border(border):
    """
    Extend the last section of a border to a large size in order to find cross points with other lanes
    :param border: list of coordinates
    :return: list of coordinates representing new extended border
    """

    return border[:-2] + extend_vector(border[-2:], backward=False)


def extend_destination_border(border):
    """
    Extend the first section of a border to a large size in order to find cross points with other lanes
    :param border: list of coordinates
    :return: list of coordinates representing new extended border
    """
    return extend_vector(border[:2]) + border[2:]


def shift_list_of_nodes(node_coordinates, widths, direction_reference=None):
    """
    Shift a list nodes to the distance of width
    :param node_coordinates: list of coordinates
    :param widths: list of widths of the lane
    :param direction_reference: reference vector used to define shift direction
    :return: shifted list of coordinates
    """

    if len(node_coordinates) < 2 or len(node_coordinates) > len(widths):
        return node_coordinates

    shifted_list = [shift_vector(node_coordinates, widths[0], direction_reference)[0]]
    x0 = node_coordinates[0][0]
    y0 = node_coordinates[0][1]
    i = 1
    for x1, y1 in node_coordinates[1:]:
        shifted_list.append(shift_vector([(x0, y0), (x1, y1)], widths[i], direction_reference)[1])
        x0 = x1
        y0 = y1
        i += 1

    return shifted_list


def get_vertices(node_coordinates, width):
    """
    Get list of points for a polygon
    :param node_coordinates:
    :param width: width of the lane (m)
    :return: list of coordinates
    """

    if len(node_coordinates) < 2:
        return None

    return shift_list_of_nodes(node_coordinates, [width]*len(node_coordinates)) + node_coordinates[::-1]


def cut_border_by_distance(line, distance):
    """
    Cut a border in two pieces at a specified distance from the beginning
    :param line: LineString
    :param distance: float
    :return: list of two LineStrings
    """
    if distance <= 0.0 or distance >= line.length:
        return [geom.LineString(line)]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(geom.Point(p))
        if pd == distance:
            return [
                geom.LineString(coords[:i+1]),
                geom.LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                geom.LineString(coords[:i] + [(cp.x, cp.y)]),
                geom.LineString([(cp.x, cp.y)] + coords[i:])]


def get_compass(x, y):
    return get_compass_bearing(x[::-1], y[::-1])


def get_compass_bearing(pointA, pointB):
    """
    Calculates the bearing between two points.
    The formulae used is the following:
        θ = atan2(sin(Δlong).cos(lat2),
                  cos(lat1).sin(lat2) − sin(lat1).cos(lat2).cos(Δlong))
    :Parameters:
      - `pointA: The tuple representing the latitude/longitude for the
        first point. Latitude and longitude must be in decimal degrees
      - `pointB: The tuple representing the latitude/longitude for the
        second point. Latitude and longitude must be in decimal degrees
    :Returns:
      The bearing in degrees
    :Returns Type:
      float
    """
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
                                           * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180° to + 180° which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing


def get_lane_bearing(lane):
    """
    Get compass bearing of a lane
    :param lane: dictionary
    :return: float (degrees)
    """
    if len(lane['left_border']) < 2:
        return None
    x0 = lane['left_border'][0][0]
    y0 = lane['left_border'][0][1]
    x1 = lane['left_border'][-1][0]
    y1 = lane['left_border'][-1][1]
    return get_compass_bearing((y0, x0), (y1, x1))


def to_rad(degree):
    """
    Covert radiance to degrees
    :param degree: float
    :return: float
    """
    return degree/360.0*2.0*math.pi


def get_compass_rhumb(compass_bearing):
    """
    Convert bearing in degrees to an 8-point compass rhumb
    :param compass_bearing: float
    :return: string
    """
    interval = 360.0/len(rhumbs)
    return rhumbs[int(float(compass_bearing)/interval + 0.5) % len(rhumbs)]


def set_lane_bearing(lanes):
    """
    Set compass bearings and rhumbs for a list of lanes
    :param lanes: list of dictionaries
    :return: None
    """
    for lane in lanes:
        lane['bearing'] = get_lane_bearing(lane)
        lane['compass'] = get_compass_rhumb(lane['bearing'])


def normalized_compass(starting_compass, turn_angle):
    """
    Convert starting and ending angles of a left turn from compass bearing to normal angles in degrees
    :param starting_compass: float
    :param turn_angle: float
    :return: tuple of floats
    """
    starting_angle = (- starting_compass + 90)
    ending_angle = starting_angle + turn_angle
    if starting_angle > 360.0 or ending_angle > 360.0:
        starting_angle -= 360.0
        ending_angle -= 360.0
    elif starting_angle < -360.0 or ending_angle < -360.0:
        starting_angle += 360.0
        ending_angle += 360.0

    return starting_angle, ending_angle


def vector_len(coord):
    x0 = coord[0][0]
    y0 = coord[0][1]
    x1 = coord[1][0]
    y1 = coord[1][1]
    return ox.great_circle_vec(y0, x0, y1, x1)


def get_incremental_points((x0, y0), (x1, y1), n, l):
    """
    Create a sequence of n+1 points along the vector.
    Combined distance of n interval between n+1 points should be l.
    l can be smaller or larger than the vector length
    :param x0: starting vector coordinate
    :param y0: starting vector coordinate
    :param x1: ending vector coordinate
    :param y1: ending vector coordinate
    :param n: number of points
    :param l: combined distance, m
    :return: list of coordinates
    """

    if n < 1:
        return None

    vector_length = ox.great_circle_vec(y0, x0, y1, x1)
    if vector_length < 0.01:
        return None

    scale = l/vector_length
    return [(x0+(x1-x0)*i/n*scale, y0+(y1-y0)*i/n*scale) for i in range(n+1)]


def cut_border_by_polygon(border, polygon, multi_string_index=0):
    """
    Remove a portion of a border that overlaps wit a polygon
    :param border: list of coordinates
    :param polygon: polygon
    :param multi_string_index: either -1 if the border direction is from intersection or 0 otherwise
    :return: list of coordinates
    """
    b = geom.LineString(border)

    if not b.intersects(polygon):
        return border

    shortened_border = b.difference(polygon)
    if type(shortened_border) is geom.multilinestring.MultiLineString:
        shortened_border = list(shortened_border)[multi_string_index]
    try:
        list_of_coordinates = list(shortened_border.coords)
    except Exception as e:
        print('Exception:',  e)
        print('Type ', type(shortened_border))
        return None
    return list_of_coordinates


def get_turn_angle(origin_border, destination_border):
    """
    Step 4.  Intersect two borders and return intersection angle.
    Returns three objects: an intersection point, vector along the origin lane border
    and vector along the destination lane border.
    :param origin_border: list of coordinates
    :param destination_border: list of coordinates
    :return: tuple of three objects: (tuple of coordinates, list of coordinates, list of coordinates)
    """

    origin_line = geom.LineString(extend_origin_border(origin_border))
    destination_line = geom.LineString(extend_destination_border(destination_border))

    if not origin_line.intersects(destination_line):
        # Something went terribly wrong
        return None, None, None

    intersection_point = origin_line.intersection(destination_line)
    pt = list(intersection_point.coords)[0]
    line2 = cut_border_by_distance(destination_line, destination_line.project(intersection_point))[1]
    return pt, [pt, origin_border[-1]], list(line2.coords)[:2]
