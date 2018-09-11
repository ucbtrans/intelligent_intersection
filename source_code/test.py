#!python
'''
Testing II.

'''

import sys
import api
import matplotlib as plt
from kml_routines import KML



# ==============================================================================
# Main function - for standalone execution.
# ==============================================================================

def main(argv):
    print(__doc__)

    city_name = "Berkeley, California, USA"
    osm_file = "maps/ComponentDr_NorthFirstSt_SJ.osm"

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

    my_gw, my_rw, my_bw = [], [], []

    for g in guideways:
        if g['type'] == 'drive':
            my_gw.append(g)
        if g['type'] == 'railway':
            my_rw.append(g)
        if g['type'] == 'bicycle':
            my_bw.append(g)


    kml_file = 'GG0.kml'
    my_kml = KML()
    my_kml.crosswalk_medians(crosswalks, width=3)
    my_kml.guideway_medians(my_rw, color="ff00BBBB", width=3)
    my_kml.guideway_medians(my_bw, color="ff00DD00", width=2)
    my_kml.guideway_medians(my_gw, width=3)
    my_kml.save(kml_file)


    main_idx = ['[416208098]-[554701, 470102]']
    c_idx = ['503335189', '503335191']
    g_idx = ['[416208100]-[554701, 470102]', '[416208100]-[810501, 50102]', '[416208100]-[416210123, 25927195001]']
    r_idx = ['[729401]-[940102]', '[756701]-[670102]']
    b_idx = ['[25927195000]-[810501, 50102]', '[416208100]-[554701, 470102]']

    main_gw, my_cw, my_gw, my_rw, my_bw = [], [], [], [], []
    bz_gw_id = 0

    # crosswalks
    for cw in crosswalks:
        my_id = "{}".format(cw['path_id'])
        if my_id in c_idx:
            my_cw.append(cw)

    for gw in guideways:
        my_id = "{}-{}".format(gw['origin_lane']['path_id'], gw['destination_lane']['path_id'])

        if my_id in main_idx:
            main_gw.append(gw)
            continue

        if gw['type'] == 'drive' and my_id in g_idx:
            my_gw.append(gw)
            if my_id == g_idx[0]:
                bz_gw_id = gw['id']
            continue

        if gw['type'] == 'railway' and my_id in r_idx:
            my_rw.append(gw)
            continue

        if gw['type'] == 'bicycle' and my_id in b_idx:
            my_bw.append(gw)
            continue

    conflict_zones = api.get_conflict_zones(main_gw[0], my_gw+my_rw+my_bw+my_cw)
    my_cz = conflict_zones[6]
    for cz in conflict_zones:
        if cz['guideway2_id'] == bz_gw_id:
            my_cz = cz
            break

    blocking_guideways = my_gw
    point_of_view = (0.1, 0.5)
    blind_zone = api.get_blind_zone(point_of_view, main_gw[0], my_cz, blocking_guideways, guideways)

    fig = api.get_conflict_zone_image(conflict_zones, x_section)
    fig.savefig("conflict_zones.jpg")

    #fig = api.get_blind_zone_image(blind_zone, main_gw[0], x_section, blocks=blocking_guideways)
    #fig.savefig("blind_zone.jpg")

    kml_file = 'GG.kml'
    my_kml = KML()
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