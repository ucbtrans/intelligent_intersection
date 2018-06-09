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