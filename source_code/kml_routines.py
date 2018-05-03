"""
KML export routines.
"""


import sys
import simplekml





class KML:
    
    def __init__(self):
        '''
        Constructor...
        '''

        self.kml = simplekml.Kml()
        
        return



    def guideway_medians(self, gw_list, color="ffff0000", width=2):
        '''

        :param gw_list:
        :return:
        '''

        for gw in gw_list:
            name = "{} {} - {} {} ({})".format(gw['origin_lane']['name'], gw['origin_lane']['compass'],
                                               gw['destination_lane']['name'], gw['destination_lane']['compass'],
                                               gw['direction'])
            description = "Approach: {} {} (lane {})\nExit: {} {} (lane {})\nDirection: {}\nType: {}".format(gw['origin_lane']['name'],
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
                coords.append((gw['median'][i][0], gw['median'][i][1], 0))
            ls.coords = coords
            ls.extrude = 1
            ls.altitudemode = simplekml.AltitudeMode.relativetoground

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


