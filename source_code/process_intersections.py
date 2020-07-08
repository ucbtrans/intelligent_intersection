'''
Process selected intersections.

'''

import sys
import api
import logging
import csv
import geodata_export as geo
from kml_routines import KML
from ast import literal_eval
import posixpath
import random
import json
import pickle


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s',
                    stream=sys.stdout,
                    #filename='mylog.log',
                    filemode='w+')





# ==============================================================================
# Auxiliary functions
# ==============================================================================

def extract_street_names(buf):
    '''
    Extract street names from the buffer formatted as "('<street_name_1>', '<street_name_2>')".

    :return:
        List of street names.
    '''

    streets = literal_eval(buf)

    return list(streets)



def filter_guideways(guideways, ignored_directions):
    '''
    Remove guideways for specified directions.

    :param guideways:
    :param ignored_directions:

    :return:
        Updated guideway list.
    '''

    updated = []
    for gw in guideways:
        if gw['direction'] in ignored_directions:
            continue
        updated.append(gw)

    return updated





#==============================================================================
# API
#==============================================================================

def generate_intersection_list(args):
    '''
    Generate the list of intersections for a given city.

    :param args:
        Dictionary with function arguments:
            args['city_name'] = Name of the city. E.g., 'San Francisco, California, USA'.
            args['data_dir'] = Name of the data directory where the output should be placed.
            args['crop_radius'] = Crop radius for intersection extraction. Default = 80.
            args['debug'] = (Optional) Boolean parameter indicating whether DEBUG info must be logged.

    :returns res:
        Dictionary with resulting info:
            res['intersections_signalized'] = List of signalized intersections.
            res['intersections_other'] = List of all other intersections.
            res['failed'] = List of intersections, for which data could not be extracted.

    '''

    if args == None:
        return None

    city_name = args['city_name']
    data_dir = args['data_dir']
    output_signalized = "{}/{}_signalized.csv".format(data_dir, city_name)
    output_other = "{}/{}_other.csv".format(data_dir, city_name)
    output_nosignal = "{}/{}_nosignal.csv".format(data_dir, city_name)
    output_failed = "{}/{}_failed.csv".format(data_dir, city_name)
    pickle_res = "{}/{}.pickle".format(data_dir, city_name)

    crop_radius = 80
    if 'crop_radius' in args.keys():
        crop_radius = args['crop_radius']

    debug = False
    if 'debug' in args.keys():
        debug = args['debug']

    city = api.get_data(city_name=city_name)
    cross_streets = api.get_intersecting_streets(city)
    #cross_streets = random.sample(cross_streets, 50)

    fp_s = open(output_signalized, 'w')
    fp_n = open(output_nosignal, 'w')
    fp_o = open(output_other, 'w')
    fp_f = open(output_failed, 'w')

    first_s, first_n, first_o, first_f = True, True, True, True
    header = "Intersection,Longitude,Latitude"
    meta_keys = []
    key_count = 0

    res = {'intersections_signalized': [], 'intersections_nosignal': [], 'intersections_other': [], 'failed': []}
    idx = 1
    cnt_s, cnt_n, cnt_o, cnt_f = 0, 0, 0, 0
    prct = 0
    sz = len(cross_streets)

    for cs in cross_streets:
        try:
            intersection = api.get_intersection(cs, city, crop_radius=crop_radius)
            lon, lat = intersection['center_x'], intersection['center_y']
            meta = intersection['meta_data']
            signalized, other = False, False
            if meta['signal_present'] == "yes":
                signalized = True
            if meta['signal_present'] == None:
                other = True

            if len(meta_keys) == 0:
                for k in meta.keys():
                    if k != "timestamp":
                        if k == 'approach_counts':
                            header += ",oneway_approach_count,twoway_approach_count,singleway_approach_count"
                        elif k == 'exit_counts':
                            header += ",oneway_exit_count,twoway_exit_count,singleway_exit_count"
                        else:
                            header += ",{}".format(k)
                        meta_keys.append(k)
                        key_count += 1
                header += "\n"

            buf = "\"{}\",{},{}".format(cs, lon, lat)
            for k in range(key_count):
                if meta_keys[k] == 'approach_counts' or meta_keys[k] == 'exit_counts':
                    buf += ",{},{},{}".format(meta[meta_keys[k]]['oneway'], meta[meta_keys[k]]['twoway'], meta[meta_keys[k]]['singleway'])
                elif meta_keys[k] == 'approach_street_types' or meta_keys[k] == 'exit_street_types':
                    buf += ",\"{}\"".format(meta[meta_keys[k]])
                elif meta_keys[k] == 'approach_max_speed_limit' or meta_keys[k] == 'approach_min_speed_limit' or meta_keys[k] == 'exit_max_speed_limit' or meta_keys[k] == 'exit_min_speed_limit':
                    val_str = meta[meta_keys[k]].split()
                    buf += ",{}".format(val_str[0])
                else:
                    buf += ",{}".format(meta[meta_keys[k]])
            buf += "\n"

            if signalized:
                res['intersections_signalized'].append(intersection)
                if first_s:
                    fp_s.write(header)
                    first_s = False
                fp_s.write(buf)
                cnt_s += 1
            elif other:
                res['intersections_other'].append(intersection)
                if first_o:
                    fp_o.write(header)
                    first_o = False
                fp_o.write(buf)
                cnt_o += 1
            else:
                res['intersections_nosignal'].append(intersection)
                if first_n:
                    fp_n.write(header)
                    first_n = False
                fp_n.write(buf)
                cnt_n += 1
        except:
            res['failed'].append(cs)
            if first_f:
                fp_f.write("Intersection\n")
                first_f = False
            fp_f.write("\"{}\"\n".format(cs))
            cnt_f += 1

        new_prct = 100 * idx / sz
        print(cs, cnt_s, cnt_n, cnt_o, 'Fail=%d'%cnt_f, meta['diameter'], idx, sz, new_prct, prct)
        if new_prct - prct >= 1:
            prct = new_prct
            if debug:
                logging.debug("process_intersections.generate_intersection_list(): Generated {}% ({} signalized, {} without signal, {} other, {} failed out of {}).".format(int(prct), cnt_s, cnt_n, cnt_o, cnt_f, sz))
        idx += 1

    fp_s.close()
    fp_n.close()
    fp_o.close()
    fp_f.close()

    if False:
        f = open(pickle_res, 'wb')
        pickle.dump(res, f)
        f.close()

    return res



def extract_intersection(args):
    '''
    Process selected intersections listed in a given CSV file.

    :param args:
        Dictionary with function arguments:
            args['city_name'] = Name of the city. E.g., 'San Francisco, California, USA'.
            args['osm_file'] = Name of the OSM file.
            args['cross_streets'] = List [<street_name_1>, <street_name_2>, ...] pointing to an intersection.
            args['crop_radius'] = Crop radius for intersection extraction. Default = 80.
            args['debug'] = (Optional) Boolean parameter indicating whether DEBUG info must be logged.

    :returns res:
        Dictionary with resulting info:
            res['intersection'] = Dictionary with intersection data.
    '''

    if args == None:
        return None

    city_name = args['city_name']
    osm_file = args['osm_file']
    cross_streets = args['cross_streets']

    crop_radius = 80
    if 'crop_radius' in args.keys():
        crop_radius = args['crop_radius']

    debug = False
    if 'debug' in args.keys():
        debug = args['debug']

    #city_area = api.get_data(file_name=osm_file)
    city_area = api.get_data(city_name=city_name)
    intersecting_streets = api.get_intersecting_streets(city_area)
    intersection_addr = None

    for ia in intersecting_streets:
        isin = True
        for cs in cross_streets:
            isin &= cs in ia
        if isin:
            intersection_addr = ia

    intersection = api.get_intersection(intersection_addr, city_area, crop_radius=crop_radius)

    res = {'intersection': intersection}

    return res



def process_intersections(args):
    '''
    Process selected intersections listed in a given CSV file.

    :param args:
        Dictionary with function arguments:
            args['intersections_file'] = CSV file with the list of intersections.
            args['id_list'] = List of intersection IDs in the list.
            args['maps_dir'] = Name of the maps directory.
            args['ignored_directions'] = (Optional) List of guideway directions to ignore. Possible directions are:
                                         + 'through';
                                         + 'right';
                                         + 'left';
                                         + 'u_turn'.
            args['crop_radius'] = Crop radius for intersection extraction. Default = 80.
            args['debug'] = (Optional) Boolean parameter indicating whether DEBUG info must be logged.

    :returns res:
        Dictionary with resulting info:
            res['intersection'] = Dictionary with intersection data.
            res['guideways'] = List of guideways. Each guideway is a dictionary.
            res['crosswalk'] = List of crosswalks. Each crosswalk is a dictionary.
    '''

    if args == None:
        return None

    city_name = args['city_name']
    intersections_file = args['intersections_file']
    id_list = args['id_list']
    maps_dir = args['maps_dir']

    ignored_directions = []
    if 'ignored_directions' in args.keys():
        ignored_directions = args['ignored_directions']

    crop_radius = 80
    if 'crop_radius' in args.keys():
        crop_radius = args['crop_radius']

    debug = False
    if 'debug' in args.keys():
        debug = args['debug']

    with open(intersections_file, 'r') as f:
        reader = csv.reader(f)
        #next(reader)  # skip header
        data = [r for r in reader]
        f.close()

    res = dict()

    sz = len(data)
    for i in range(sz):
        if i in id_list:
            osm_file = posixpath.join(maps_dir, data[i][2])
            cross_streets = extract_street_names(data[i][0])
            metafiles = literal_eval(data[i][3])
            traces = literal_eval(data[i][4])
            args2 = {'city_name': city_name, 'osm_file': osm_file, 'cross_streets': cross_streets, 'crop_radius': crop_radius, 'debug': debug}
            res0 = extract_intersection(args2)
            intersection = res0['intersection']
            guideways = api.get_guideways(intersection)
            guideways = filter_guideways(guideways, ignored_directions)
            crosswalks = api.get_crosswalks(intersection)
            info = {'intersection': intersection, 'guideways': guideways, 'crosswalks': crosswalks, 'metafiles': metafiles, 'traces': traces}
            res[i] = info

    return res




# ==============================================================================
# Main function - for standalone execution.
# ==============================================================================

def main(argv):
    print(__doc__)

    maps_dir = "maps"
    city_name = "San Francisco, California, USA"
    data_dir = "intersections"
    input_file = "intersections.csv"
    #input_file = "intersections0.csv"
    ignored_directions = ['u_turn']
    crop_radius = 80
    debug = True

    args = {'city_name': city_name, 'data_dir': data_dir, 'crop_radius': crop_radius, 'debug': debug}
    generate_intersection_list(args)

    if False:
        return

    intersections_file = posixpath.join(maps_dir, input_file)

    id_list = [2, 4, 5, 7, 10, 11, 14]
    id_list = [4, 5, 6]

    args = {'city_name': city_name, 'maps_dir': maps_dir, 'intersections_file': intersections_file, 'id_list': id_list, 'ignored_directions': ignored_directions, 'crop_radius': crop_radius, 'debug': debug}
    res = process_intersections(args)

    for k in res.keys():
        kmlguideways = "{}/guideways_{}.kml".format(data_dir, k)
        args = {'kmlfile': kmlguideways, 'guideways': res[k]['guideways'], 'crosswalks': res[k]['crosswalks'], 'debug': debug}
        geo.export_guideways_kml(args)

        kmltraces = "{}/traces_{}.kml".format(data_dir, k)
        args = {'kmlfile': kmltraces, 'traces': res[k]['traces'], 'latlon': True, 'color': "FF990099", 'debug': debug}
        geo.export_traces_kml(args)






    if True:
        return

    city_name = "Berkeley, California, USA"
    osm_file = "../osm/ComponentDr_NorthFirstSt_SJ.osm"

    city = api.get_data(city_name=city_name)
    city = api.get_data(file_name=osm_file)
    cross_streets = api.get_intersecting_streets(city)

    sz = len(cross_streets)
    x_section_addr = cross_streets[0]
    x_section_addr = ('University Avenue', 'Acton Street')
    x_section_addr = ('North 1st Street', 'Component Drive')
    x_section = api.get_intersection(x_section_addr, city, crop_radius=50.0)
    guideways = api.get_guideways(x_section)
    crosswalks = api.get_crosswalks(x_section)

    #fig = api.get_intersection_image(x_section)
    #fig.savefig("intersection.jpg")

    fig = api.get_guideway_image(guideways, x_section)
    fig.savefig("guideways.jpg")

    #print(x_section_addr)
    #print(guideways)
    #print(crosswalks)
    main_gw = [guideways[0]]
    c_idx = [1, 3]
    g_idx = [1, 6, 9, 11]
    r_idx = [18, 19]
    b_idx = [25, 28]

    my_cw, my_gw, my_rw, my_bw = [], [], [], []

    # crosswalks
    for idx in c_idx:
        my_cw.append(crosswalks[idx])

    # vehicle guideways
    for idx in g_idx:
        my_gw.append(guideways[idx])

    # railroads
    for idx in r_idx:
        my_rw.append(guideways[idx])

    # bicycle routes
    for idx in b_idx:
        my_bw.append(guideways[idx])

    conflict_zones = api.get_conflict_zones(main_gw[0], my_gw+my_rw+my_bw+my_cw)

    blocking_guideways = my_gw
    point_of_view = (0.1, 0.5)
    blind_zone = api.get_blind_zone(point_of_view, main_gw[0], conflict_zones[4], blocking_guideways, guideways)

    fig = api.get_conflict_zone_image(conflict_zones, x_section)
    fig.savefig("conflict_zones.jpg")

    fig = api.get_blind_zone_image(blind_zone, main_gw[0], x_section, blocks=blocking_guideways)
    fig.savefig("blind_zone.jpg")

    kml_file = 'GG.kml'
    my_kml = KML()
    #my_kml.crosswalk_medians(my_cw, width=15)
    #my_kml.guideway_medians(my_gw, width=20)
    #my_kml.guideway_medians(main_gw, color="ffffff00", width=20)
    my_kml.crosswalks(my_cw)
    my_kml.guideways(my_rw, color="ff00BBBB")
    my_kml.guideways(my_bw, color="ff00DD00")
    my_kml.guideways(my_gw, color="ffff0000")
    my_kml.guideways(main_gw, color="ffffff00")
    my_kml.conflict_zones(conflict_zones)
    my_kml.blind_zones([blind_zone])
    my_kml.save(kml_file)


if __name__ == "__main__":
    main(sys.argv)