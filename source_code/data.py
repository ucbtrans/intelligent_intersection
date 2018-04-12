#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module gets input data
#
#######################################################################


import xmltodict
import osmnx as ox
import json


parameters = {'version': '@version',
              'generator': '@generator',
              'osm3s': '@copyright',
              'attribution': '@attribution',
              'license':  '@license',
              'bounds': 'bounds',
              'node': 'node',
              'way': 'way',
              'relation': 'relation'
              }

include = {'drive': ['highway']}

exclude = {
    'drive': {"area": 'yes',
              "highway": "cycleway|footway|path|pedestrian|steps|track|corridor|"
                         + "proposed|construction|bridleway|abandoned|platform|raceway|service",
              "motor_vehicle": "no",
              "motorcar": "no",
              "service": "parking|parking_aisle|driveway|private|emergency_access",
              "access": "private"
              },
    'all': {"area": 'yes',
            "highway": "proposed|construction|abandoned|platform|raceway",
            "service": "private",
            "access": "private"
            }
        }

exclude_keywords = ['landuse']


def get_data_from_file(file_name):
    """
    Get data from an XML file and covert to a dictionary
    :param file_name: string
    :return: dictionary with data
    """
    try:
        with open(file_name) as f:
            raw_dict = xmltodict.parse(f.read())
            ways = [w for w in clean_list(raw_dict['osm']['way'], element_type='way') if filter_out(w)]
            nodes = clean_list(raw_dict['osm']['node'], element_type='node')
            relations = clean_list(raw_dict['osm']['relation'], element_type='relation')
            selection = [{'version': parse_xml_parameter('version', raw_dict),
                          'osm3s': parse_xml_parameter('osm3s', raw_dict),
                          'generator': parse_xml_parameter('generator', raw_dict),
                          'bounds': parse_xml_parameter('bounds', raw_dict),
                          'elements': ways + nodes + relations
                          }
                         ]
        return selection
    except IOError, xmltodict.ExpatError:
        return None


def clean_element(e, element_type='way'):
    """
    Clean element dictionary from garbage coming from XML to dictionary conversion.
    Also adding element type because it is missing in the raw data.
    :param e: dictionary
    :param element_type: string
    :return: cleaned dictionary
    """
    cleaned = {'type': element_type, 'tags': {}}
    e_dict = json.loads(json.dumps(e))
    for key in e_dict:
        if key == 'nd':
            if isinstance(e_dict['nd'], list):
                nd_list = e_dict['nd']
            else:
                nd_list = [e_dict['nd']]
            cleaned['nodes'] = [int(nd['@ref']) for nd in nd_list]
            continue

        if key == 'tag':
            if isinstance(e_dict['tag'], list):
                tag_list = e_dict['tag']
            else:
                tag_list = [e_dict['tag']]
            cleaned['tags'] = {t['@k']: t['@v'] for t in tag_list}
            continue

        if key == '@id':
            cleaned['id'] = int(e_dict[key])
            continue

        if key == 'lat' or key == '@lat' or key == 'lon' or key == '@lon':
            cleaned[key.replace('@', '')] = float(e_dict[key])
            continue

        cleaned[key.replace('@', '')] = e_dict[key]

    return cleaned


def clean_list(lst, element_type='way'):
    """
    Cleaning a list of elements from XML garbage and adding types.
    :param lst: list of dictionaries
    :param element_type: string
    :return: list of cleaned dictionaries
    """
    return [clean_element(e, element_type=element_type) for e in lst]


def filter_out(path_data):
    """
    Filtering out inapplicable elements.
    :param path_data: dictionary
    :return: True if the element should stay in, otherwise False
    """
    for key in exclude_keywords:
        if key in path_data['tags']:
            return False
    return True


def check_network(network_type, path_data):
    """
    Check if a path matches the specified network type
    :param network_type: string
    :param path_data: dictionary
    :return: True if matches, False otherwise
    """

    if network_type in include and 'tags' in path_data:
        for keyword in include[network_type]:
            if keyword not in path_data['tags']:
                return False

    if network_type not in exclude or 'tags' not in path_data:
        return True

    for key in exclude[network_type]:
        if key in path_data['tags'] and path_data['tags'][key] in exclude[network_type][key]:
            return False

    return True


def check_infrastructure(infrastructure, data):
    """
    Check if an element matches the specified infrastructure
    :param infrastructure: string
    :param data: dictionary
    :return: True if matches, False otherwise
    """
    if infrastructure == 'way["highway"]':
        if data['type'] == 'way' and 'tags' in data and 'highway' in data['tags']:
            return True
        else:
            return False
    elif infrastructure == 'way["railway"]':
        if data['type'] == 'way' and 'tags' in data and 'railway' in data['tags']:
            return True
        else:
            return False
    elif infrastructure == 'node["highway"]':
        if data['type'] == 'node' and 'tags' in data and 'highway' in data['tags']:
            return True
        else:
            return False
    else:
        return True


def get_data_subset(selection, network_type='drive', infrastructure='way["highway"]'):
    """
    Get data subset for a specified infrastructure
    :param selection: osmnx data structure
    :param network_type: string
    :param infrastructure: string
    :return: osmnx data structure
    """
    paths = []
    nodes = []
    if infrastructure == 'node["highway"]':
        nodes = [n for n in selection[0]['elements'] if n['type'] == 'node' and 'tags' in n and 'highway' in n['tags']]
    else:
        paths = [p for p in selection[0]['elements'] if p['type'] == 'way'
                 and check_infrastructure(infrastructure, p)
                 and check_network(network_type, p)
                 ]

    if not nodes:
        node_ids = []
        for p in paths:
            if 'nodes' not in p:
                continue
            node_ids.extend(p['nodes'])

        nodes = [n for n in selection[0]['elements'] if n['id'] in node_ids]

    return [{'version': selection[0]['version'],
             'osm3s': selection[0]['osm3s'],
             'generator': selection[0]['generator'],
             'bounds': selection[0]['bounds'],
             'elements': paths + nodes
             }
            ]


def parse_xml_parameter(par, raw_dict):
    """
    Parse a single parameter from XML converted to a dictionary
    :param par: string
    :param raw_dict: dictionary
    :return: string
    """
    if 'osm' in raw_dict and parameters[par] in raw_dict['osm']:
        if par == 'bounds':
            coord = {}
            for key in raw_dict['osm'][parameters[par]]:
                coord[key] = float(raw_dict['osm'][parameters[par]][key])
            return coord
        else:
            return raw_dict['osm'][parameters[par]]
    else:
        return ''


def get_box_from_xml(bounds):
    """
    Define north, south, east, west from XML data
    :param bounds: dictionary of lat and lon
    :return: four floats: north, south, east, west 
    """
    return bounds['@maxlat'], bounds['@minlat'], bounds['@maxlon'], bounds['@minlon'],


def get_city_from_osm(city_name, network_type="drive"):
    """
    Get city data from OSM as an osmnx data structure.
    :param city_name: city name like 'Campbell, California, USA'
    :param network_type: string: {'walk', 'bike', 'drive', 'drive_service', 'all', 'all_private', 'none'}
    :return: city data structure
    """
    city_paths_nodes = None
    for which_result in range(1, 4):
        try:
            city_boundaries = ox.gdf_from_place(city_name, which_result=which_result)
            city_paths_nodes = ox.osm_net_download(city_boundaries['geometry'].unary_union, network_type=network_type)
            break
        except ValueError:
            continue
    if city_paths_nodes is None:
        return None


def get_box_data(x_data, selection, network_type='all', infrastructure='way["highway"]'):
    """
    Get data for an intersection within a box.  
    If the city data came from a file, return a subset of nodes and paths based on the network type and infrastructure,
    otherwise download data from OSM online.
    :param x_data: intersection dictionary
    :param selection: osmnx data structure obtained from the XML file.  
    :param network_type: string
    :param infrastructure: string
    :return: osmnx data structure
    """
    if x_data['from_file'] == 'yes':
        return get_data_subset(selection, network_type=network_type, infrastructure=infrastructure)
    else:
        return ox.osm_net_download(north=x_data['north'],
                                   south=x_data['south'],
                                   east=x_data['east'],
                                   west=x_data['west'],
                                   network_type=network_type,
                                   infrastructure=infrastructure
                                   )
