"""
KML export routines.
"""


import sys
import simplekml





class KML:
    
    def __init__(self, elevation=3):
        '''
        Constructor...
        '''

        self.kml = simplekml.Kml()
        self.elevation = elevation
        
        return



    def guideway_medians(self, gw_list, color="ffff0000", width=3):
        '''

        :param gw_list:
        :param color:
        :param width:
        :return:
        '''

        k = 0
        for gw in gw_list:
            name = "({}) {} {} - {} {} ({})".format(k, gw['origin_lane']['name'], gw['origin_lane']['compass'],
                                                    gw['destination_lane']['name'], gw['destination_lane']['compass'],
                                                    gw['direction'])
            description = "ID: {}-{}\nApproach: {} {} (lane {})\nExit: {} {} (lane {})\nDirection: {}\nType: {}".format(gw['origin_lane']['path_id'],
                                                                                                             gw['destination_lane']['path_id'],
                                                                                                             gw['origin_lane']['name'],
                                                                                                             gw['origin_lane']['compass'],
                                                                                                             gw['origin_lane']['lane_id'],
                                                                                                             gw['destination_lane']['name'],
                                                                                                             gw['destination_lane']['compass'],
                                                                                                             gw['destination_lane']['lane_id'],
                                                                                                             gw['direction'],
                                                                                                             gw['type'])
            mg = self.kml.newmultigeometry()
            mg.name = name
            mg.description = description
            ls = mg.newlinestring()
            ls.style.linestyle.width = width
            ls.style.linestyle.color = color

            coords = []
            sz = len(gw['median'])
            for i in range(sz):
                coords.append((gw['median'][i][0], gw['median'][i][1], self.elevation))
            ls.coords = coords
            #ls.extrude = 1
            #ls.altitudemode = simplekml.AltitudeMode.relativetoground
            ls.altitudemode = simplekml.AltitudeMode.clamptoground
            k += 1

        return



    def guideways(self, gw_list, color="ffff0000"):
        '''

        :param gw_list:
        :param color:
        :return:
        '''

        k = 0
        for gw in gw_list:
            name = "({}) {} {} - {} {} ({})".format(k, gw['origin_lane']['name'], gw['origin_lane']['compass'],
                                                    gw['destination_lane']['name'], gw['destination_lane']['compass'],
                                                    gw['direction'])
            description = "ID: {}-{}\nApproach: {} {} (lane {})\nExit: {} {} (lane {})\nDirection: {}\nType: {}".format(gw['origin_lane']['path_id'],
                                                                                                             gw['destination_lane']['path_id'],
                                                                                                             gw['origin_lane']['name'],
                                                                                                             gw['origin_lane']['compass'],
                                                                                                             gw['origin_lane']['lane_id'],
                                                                                                             gw['destination_lane']['name'],
                                                                                                             gw['destination_lane']['compass'],
                                                                                                             gw['destination_lane']['lane_id'],
                                                                                                             gw['direction'],
                                                                                                             gw['type'])
            mg = self.kml.newmultigeometry()
            mg.name = name
            mg.description = description
            pol = mg.newpolygon()
            pol.style.linestyle.width = 1
            pol.style.linestyle.color = color
            pol.style.polystyle.color = color

            coords = []
            for lnglat in gw['left_border']:
                coords.append((lnglat[0], lnglat[1], self.elevation))
            for lnglat in reversed(gw['right_border']):
                coords.append((lnglat[0], lnglat[1], self.elevation))
            pol.outerboundaryis = coords
            #pol.extrude = 10
            #pol.altitudemode = simplekml.AltitudeMode.relativetoground
            pol.altitudemode = simplekml.AltitudeMode.clamptoground
            k += 1

        return




    def crosswalk_medians(self, cw_list, color="ff0000bb", width=2):
        '''

        :param cw_list:
        :param color:
        :param width:
        :return:
        '''

        k = 0
        for cw in cw_list:
            name = "({}) {}: {} {} ({} m)".format(k, cw['lane_type'], cw['name'], cw['compass'], cw['width'])
            description = "ID: {}\nName: {} {} \nWidth: {} m\nType: {}".format(cw['path_id'], cw['name'], cw['compass'], cw['width'], cw['type'])
            mg = self.kml.newmultigeometry()
            mg.name = name
            mg.description = description
            ls = mg.newlinestring()
            ls.style.linestyle.width = width
            ls.style.linestyle.color = color

            coords = []
            sz = len(cw['median'])
            for i in range(sz):
                coords.append((cw['median'][i][0], cw['median'][i][1], self.elevation))
            ls.coords = coords
            #ls.extrude = 1
            #ls.altitudemode = simplekml.AltitudeMode.relativetoground
            ls.altitudemode = simplekml.AltitudeMode.clamptoground
            k += 1

        return



    def crosswalks(self, cw_list, color="ff0000bb"):
        '''

        :param cw_list:
        :param color:
        :return:
        '''

        k = 0
        for cw in cw_list:
            name = "({}) {}: {} {} ({} m)".format(k, cw['lane_type'], cw['name'], cw['compass'], cw['width'])
            description = "ID: {}\nName: {} {} \nWidth: {} m\nType: {}".format(cw['path_id'], cw['name'], cw['compass'], cw['width'], cw['type'])
            mg = self.kml.newmultigeometry()
            mg.name = name
            mg.description = description
            pol = mg.newpolygon()
            pol.style.linestyle.width = 1
            pol.style.linestyle.color = color
            pol.style.polystyle.color = color

            coords = []
            for lnglat in cw['left_border']:
                coords.append((lnglat[0], lnglat[1], self.elevation))
            for lnglat in reversed(cw['right_border']):
                coords.append((lnglat[0], lnglat[1], self.elevation))
            pol.outerboundaryis = coords
            #pol.extrude = 1
            #pol.altitudemode = simplekml.AltitudeMode.relativetoground
            pol.altitudemode = simplekml.AltitudeMode.clamptoground
            k += 1

        return



    def conflict_zones(self, cz_list, color="ffdd00dd"):
        '''

        :param cz_list:
        :param color:
        :return:
        '''

        k = 0
        for cz in cz_list:
            name = "({}) Conflict Zone {} ({}) - {} x {}".format(k, cz['id'], cz['type'], cz['guideway1_id'], cz['guideway2_id'])
            description = "ID: {}\nType: {}\nGuideway 1: {}\nGuideway 2: {}".format(cz['id'], cz['type'], cz['guideway1_id'], cz['guideway2_id'])
            mg = self.kml.newmultigeometry()
            mg.name = name
            mg.description = description
            pol = mg.newpolygon()
            pol.style.linestyle.width = 1
            pol.style.linestyle.color = color
            pol.style.polystyle.color = color

            poly = cz['polygon'].exterior.coords.xy
            sz = len(poly[0])

            coords = []
            for i in range(sz):
                coords.append((poly[0][i], poly[1][i], self.elevation))

            pol.outerboundaryis = coords
            #pol.extrude = 1
            #pol.altitudemode = simplekml.AltitudeMode.relativetoground
            pol.altitudemode = simplekml.AltitudeMode.clamptoground
            k += 1

        return



    def blind_zones(self, bz_list, color="ff000000"):
        '''

        :param bz_list:
        :param color:
        :return:
        '''

        k = 0
        for bz in bz_list:
            name = "({}) Blind Zone for Guideway {} and Conflict Zone {}".format(k, bz['guideway_id'], bz['conflict_zone']['id'])
            description = "My Guideway: {}\nConflict Zone: {}\nConflict Zone Type: {}\nPoint of View: {}\nBlocking Guideways: {}".format(
                          bz['guideway_id'], bz['conflict_zone']['id'], bz['conflict_zone']['type'], bz['point'], bz['blocking_ids'])
            mg = self.kml.newmultigeometry()
            mg.name = name
            mg.description = description
            pol = mg.newpolygon()
            pol.style.linestyle.width = 1
            pol.style.linestyle.color = color
            pol.style.polystyle.color = color

            poly = bz['polygon'].exterior.coords.xy
            sz = len(poly[0])

            coords = []
            for i in range(sz):
                coords.append((poly[0][i], poly[1][i], self.elevation))

            pol.outerboundaryis = coords
            #pol.extrude = 1
            #pol.altitudemode = simplekml.AltitudeMode.relativetoground
            pol.altitudemode = simplekml.AltitudeMode.clamptoground


            pnt = mg.newpoint()
            pnt.name = "Point of View {} in Guideway {}".format(bz['point'], bz['guideway_id'])
            pnt.coords = [(bz['geo_point'][0], bz['geo_point'][1], self.elevation)]

            k += 1

        return



    def traces(self, tr_list, latlon=False, color="ff999999", width=2):
        '''

        :param tr_list:
        :param latlon:
        :param color:
        :param width:
        :return:
        '''

        k = 0
        for tr in tr_list:
            name = "Trace {}".format(k)

            mg = self.kml.newmultigeometry()
            mg.name = name
            ls = mg.newlinestring()
            ls.style.linestyle.width = width
            ls.style.linestyle.color = color

            coords = []
            for gc in tr:
                if latlon:
                    coords.append((gc[1], gc[0], self.elevation))
                else:
                    coords.append((gc[0], gc[1], self.elevation))
            ls.coords = coords
            #ls.extrude = 1
            #ls.altitudemode = simplekml.AltitudeMode.relativetoground
            ls.altitudemode = simplekml.AltitudeMode.clamptoground
            k += 1

        return







    def save(self, kml_file):
        '''
        Save KML to a file.
        '''

        self.kml.save(kml_file)
        
        return








#==============================================================================
# Main function.
#==============================================================================
def main(argv):
    print(__doc__)
    
    






if __name__ == "__main__":
    main(sys.argv)


