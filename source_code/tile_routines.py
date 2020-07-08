"""
tile_routines.py - routines dealing with map tiles.

 + lonlat2tilenum() returns tile indices for a given lat/lon coordinate and zoom level.
 + bbox2tiles() returns tile indices covering given bounding box at a given zoom level.
 + tile2bbox() returns lat/lon bounding box for the given map tile.
 + tilepixel2lonlat() returns lat/lon of a pixel in a given tile.
 + lonlat2tilepixel() returns pixel coordinates in the tile corresponding to
                      given lat/lon and zoom level.
 + imagepixels2lonlat() returns image pixels for given lat/lon pairs.
 + lonlat2imagepixels() returns lat/lon pairs for given image pixels.
 + get_tile_url() returns URL for the specified tile.
 + get_tile() returns specified 256x256 tile from the given source.
 + tiles2image() creates an image from specified tiles and saves it to a file.
 + mask_translate() translates mask from one tile set to the other.
 + poly2lonlat() returns lat/lon shape for the polygon given in tile pixels.
 + multipoly2kml() saves given multipolygon into given KML file.
 
"""

import sys, io
import string
import urllib.request
import math
import numpy as np
from PIL import Image
import simplekml
from pygeotile.tile import Tile
import sys


def lonlat2tilenum(lon_deg, lat_deg, zoom=13):
    '''
    LONLAT2TILENUM determines the satellite tile covering given lat/lon position
    at the given zoom level.
    
    :param lon_deg:
        Longitude in decimal degrees.
    :type lon_deg:
        double
    :param lat_deg:
        Latitude in decimal degrees.
    :type lat_deg:
        double
    :param zoom:
        Zoom level.
    :type zoom:
        int
    
    :returns:
        Tuple (xtile, ytile).
    '''

    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom

    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)

    return (xtile, ytile)


def bbox2tiles(lon_deg, lat_deg, lon_range=0.01, lat_range=0.01, zoom=13):
    '''
    BBOX2TILES determines the satellite tile covering given lat/lon position
    at the given zoom level.
    
    :param lon_deg:
        Longitude in decimal degrees.
    :type lon_deg:
        double
    :param lat_deg:
        Latitude in decimal degrees.
    :type lat_deg:
        double
    :param lon_range:
        Longitude range (+/-) in decimal degrees.
    :type lon_range:
        double
    :param lat_range:
        Latitude range (+/-) in decimal degrees.
    :type lat_range:
        double
    :param zoom:
        Zoom level.
    :type zoom:
        int
    
    :returns:
        Tuple (xtile_min, xtile_max, ytile_min, ytile_max).
    '''

    (xtile_min, ytile_min) = lonlat2tilenum(lon_deg - lon_range, lat_deg + lat_range, zoom=zoom)
    (xtile_max, ytile_max) = lonlat2tilenum(lon_deg + lon_range, lat_deg - lat_range, zoom=zoom)

    return (xtile_min, xtile_max, ytile_min, ytile_max)


def x2tiles(east, west, north, south, lon_range=0.01, lat_range=0.01, zoom=13):
    '''
    BBOX2TILES determines the satellite tile covering given lat/lon position
    at the given zoom level.

    :param lon_deg:
        Longitude in decimal degrees.
    :type lon_deg:
        double
    :param lat_deg:
        Latitude in decimal degrees.
    :type lat_deg:
        double
    :param lon_range:
        Longitude range (+/-) in decimal degrees.
    :type lon_range:
        double
    :param lat_range:
        Latitude range (+/-) in decimal degrees.
    :type lat_range:
        double
    :param zoom:
        Zoom level.
    :type zoom:
        int

    :returns:
        Tuple (xtile_min, xtile_max, ytile_min, ytile_max).
    '''

    (xtile_min, ytile_min) = lonlat2tilenum(west, north, zoom=zoom)
    (xtile_max, ytile_max) = lonlat2tilenum(east, south, zoom=zoom)

    return (xtile_min, xtile_max, ytile_min, ytile_max)


def tile2bbox(xtile, ytile, zoom=13):
    '''
    TILE2BBOX returns lat/long coordinates of SW and NE corners of the map tile
    specified by its logitudal and latitudal indices and the zoom level.
    
    :param xtile:
        X-index of the map tile.
    :type xtile:
        int
    :param ytile:
        Y-index of the map tile.
    :type ytile:
        int
    :param zoom:
        Zoom level.
    :type zoom:
        int
    
    :returns:
        Tuple (lon_min, lon_max, lat_min, lat_max).
    '''

    n = 2.0 ** zoom

    lon_min = xtile / n * 360.0 - 180.0
    lon_max = (xtile + 1) / n * 360.0 - 180.0

    lat_min_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_min = math.degrees(lat_min_rad)
    lat_max_rad = math.atan(math.sinh(math.pi * (1 - 2 * (ytile + 1) / n)))
    lat_max = math.degrees(lat_max_rad)

    return (lon_min, lon_max, lat_min, lat_max)


def tilepixel2lonlat(x, y, xtile, ytile, zoom=13):
    '''
    TILEPIXEL2LONLAT computes lat/lon for a given pixel in a given map tile.
    
    :param x:
        pixel's x index.
    :type x:
        int
    :param y:
        pixel's y index.
    :type y:
        int
    :param xtile:
        X-index of the map tile.
    :type xtile:
        int
    :param ytile:
        Y-index of the map tile.
    :type ytile:
        int
    :param zoom:
        Zoom level.
    :type zoom:
        int
        
    :returns:
        Tuple (lon, lat).
    '''

    width = 256
    height = 256

    n = 2.0 ** zoom

    lon = (xtile + (x / width)) / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (ytile + (y / height)) / n)))
    lat = math.degrees(lat_rad)

    return (lon, lat)


def lonlat2tilepixel(lon_deg, lat_deg, zoom=13):
    '''
    LONLAT2TILEPIXEL returns the pixel coordinates in the tile corresponding
    to the given lat/lon coordinates and the given zoom level.
    
    :param lon_deg:
        Longitude in decimal degrees.
    :type lon_deg:
        double
    :param lat_deg:
        Latitude in decimal degrees.
    :type lat_deg:
        double
    :param zoom:
        Zoom level.
    :type zoom:
        int
    
    :returns:
        Tuple (x, y) representing pixel position in the tile.
        Tuple (xtile, ytile, zoom) identifying the tile.
    '''

    width = 256
    height = 256

    (xtile, ytile) = lonlat2tilenum(lon_deg=lon_deg, lat_deg=lat_deg, zoom=zoom)

    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom

    x = int((((lon_deg + 180.0) / 360.0 * n) - xtile) * width)
    y = int((((1.0 - math.log(
        math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n) - ytile) * height)

    return (x, y), (xtile, ytile, zoom)


def imagepixels2lonlat(pixels, xt_min, yt_min, zoom=13):
    '''
    IMAGEPIXELS2LONLAT computes lat/lon positions of the given image pixels
    provided its left top tile indices and zoom level.
    
    :param pixels:
        List of pixel coordinate pairs - [(x1,y1), (x2,y2), ...].
    :type pixels:
        list
    :param xt_min:
        Left most tile coordinate in the image.
    :type xt_min:
        int
    :param yt_min:
        Top most tile coordinate in the image.
    :type yt_min:
        int
    :param zoom:
        Zoom level.
    :type zoom:
        int
    
    :returns:
       Decimal lat/lon pairs in the form [(lon1,lat1), (lon2,lat2), ...]. 
        
    NOTE: This function does not take into account pixel size and assumes
          a high enough image resolution for pixel size to be insignificant.
    '''

    width = 256
    height = 256

    lonlat_pairs = []

    for pt in pixels:
        i = math.floor(pt[0] / width)
        j = math.floor(pt[1] / height)

        xtile = xt_min + i
        ytile = yt_min + j

        xx = pt[0] - i * width
        yy = pt[1] - j * height

        (lon, lat) = tilepixel2lonlat(xx, yy, xtile, ytile, zoom=zoom)
        lonlat_pairs.append((lon, lat))

    return lonlat_pairs


def lonlat2imagepixels(lonlat_pairs, xt_min, yt_min, zoom=13):
    '''
    LONLAT2TILEPIXELS computes the pixel coordinates in the image corresponding
    to the given lat/lon positions, given a zoom level and left top tile indices.
    
    :param lonlat_pairs:
        Decimal lat/lon pairs in the form [(lon1,lat1), (lon2,lat2), ...].
    :type lonlat_pairs:
        List
    :param xt_min:
        Left most tile coordinate in the image.
    :type xt_min:
        int
    :param yt_min:
        Top most tile coordinate in the image.
    :type yt_min:
        int
    :param zoom:
        Zoom level.
    :type zoom:
        int
    
    :returns:
        List of pixel coordinate pairs - [(x1,y1), (x2,y2), ...].
        
    NOTE: This function does not take into account pixel size and assumes
          a high enough image resolution for pixel size to be insignificant.
    '''

    width = 256
    height = 256

    pixels = []

    for pos in lonlat_pairs:
        (x, y), (xtile, ytile, zoom) = lonlat2tilepixel(lon_deg=pos[0], lat_deg=pos[1], zoom=zoom)

        x = x + width * (xtile - xt_min)
        y = y + height * (ytile - yt_min)

        pixels.append((x, y))

    return pixels


def get_tile_url(xtile, ytile, zoom=13, source="mapbox", ttype="mapbox.satellite"):
    '''
    GET_TILE_URL generates URL for a tile based on tile coordinates, zoom level, 
    tile source and tile type.
    
    :param xtile:
        X-index of the map tile.
    :type xtile:
        int
    :param ytile:
        Y-index of the map tile.
    :type ytile:
        int
    :param zoom:
        Zoom level.
    :type zoom:
        int
    :param source:
        Source where tiles come from: mapbox, mapquest, bing.
    :type source:
        string
    :param ttype:
        Optional parameter specifying tile type. Used only for Mapbox tiles.
        We consider: (1) "mapbox.satellite" and (2) "mapbox.mapbox-streets-v7".
    :type ttype:
        string
    
    :returns:
        URL for the tile.
    '''

    url = ""

    if source.lower() == "mapbox":
        access_token = "***************************************************"
        url = "https://api.mapbox.com/v4/{}/{}/{}/{}.png?access_token={}".format(
            ttype, zoom, xtile, ytile, access_token)
    elif source.lower() == "mapquest":
        url = "http://otile1.mqcdn.com/tiles/1.0.0/sat/{}/{}/{}.png".format(
            zoom, xtile, ytile)
    elif source.lower() == "bing":
        basic_key = "AnwqPV0H_H9ksQ6aokW3apTJWYUOc5rmBl4PJ_gMcUUSYiQVj2ZIJbTypMHMOE9B"
        # calculating quadkey
        interleaved = [None] * 2 * zoom
        interleaved[::2] = bin(ytile)[2:].zfill(zoom)
        interleaved[1::2] = bin(xtile)[2:].zfill(zoom)
        interleaved = ''.join(interleaved)
        # converting to decimal
        interleaved = int(interleaved, 2)

        def int2base(x, base):
            digs = string.digits + string.ascii_lowercase
            if x < 0:
                sign = -1
            elif x == 0:
                return '0'
            else:
                sign = 1
            x *= sign
            digits = []
            while x:
                digits.append(digs[x % base])
                x //= base
            if sign < 0:
                digits.append('-')
            digits.reverse()
            return ''.join(digits)

        # converting to base 4
        quad_key = int2base(interleaved, 4).zfill(zoom)

        url = "http://ecn.t0.tiles.virtualearth.net/tiles/a{}.png?g=5171&key={}".format(
            quad_key, basic_key)

    return url


def get_tile(xtile, ytile, zoom=13, source="mapbox", ttype="mapbox.satellite"):
    '''
    GET_TILE downloads the given tile from the given source.
    
    :param xtile:
        X-index of the map tile.
    :type xtile:
        int
    :param ytile:
        Y-index of the map tile.
    :type ytile:
        int
    :param zoom:
        Zoom level.
    :type zoom:
        int
    :param source:
        Source where tiles come from: mapbox, mapquest, bing.
    :type source:
        string
    :param ttype:
        Optional parameter specifying tile type. Used only for Mapbox tiles.
        We consider: (1) "mapbox.satellite" and (2) "mapbox.mapbox-streets-v7".
    :type ttype:
        string
    
    :returns:
        256x256 tile.
    '''

    url = get_tile_url(xtile, ytile, zoom=zoom, source=source, ttype=ttype)
    #print(url)
    tile = []

    try:
        tile = urllib.request.urlopen(url).read()
    except Exception as e:
        print("Error downloading tile {}/{}/{}.png: {}".format(zoom, xtile, ytile, e))

    return tile


def tiles2image(xt_min, xt_max, yt_min, yt_max, zoom=13,
                source="mapbox", ttype="mapbox.satellite",
                image_name="test.png"):
    '''
    TILES2IMAGE creates an image using specified x/y tile ranges, zoom level,
    tile source and tile type and saves to the specified file.
    
    :param xt_min:
        Minimum x index for the tile.
    :type xt_min:
        int
    :param xt_max:
        Maximum x index for the tile.
    :type xt_max:
        int
    :param yt_min:
        Minimum y index for the tile.
    :type yt_min:
        int
    :param yt_max:
        Maximum y index for the tile.
    :type yt_max:
        int
    :param zoom:
        Zoom level.
    :type zoom:
        int
    :param source:
        Source where tiles come from: mapbox, mapquest, bing.
    :type source:
        string
    :param ttype:
        Optional parameter specifying tile type. Used only for Mapbox tiles.
        We consider: (1) "mapbox.satellite" and (2) "mapbox.mapbox-streets-v7".
    :type ttype:
        string
    :param image_name:
        File name for the image to be saved as.
    :type image_name:
        string
    '''

    width = 256
    height = 256

    numXtiles = xt_max - xt_min + 1
    numYtiles = yt_max - yt_min + 1

    res_img = Image.new("RGBA", (numXtiles * width, numYtiles * height), (0, 0, 0, 0))

    for x in range(xt_min, xt_max + 1):
        for y in range(yt_min, yt_max + 1):
            tile = get_tile(x, y, zoom=zoom, source=source, ttype=ttype)
            img = Image.open(io.BytesIO(tile))
            res_img.paste(img, ((x - xt_min) * width, (y - yt_min) * height))

    res_img.save(image_name)

    return res_img


def x2bbox(xt_min, xt_max, yt_min, yt_max, zoom=19):
    south = 90.0
    north = -90.0
    east = -180.0
    west = 180.0

    for x in range(xt_min, xt_max + 1):
        for y in range(yt_min, yt_max + 1):
            tile = Tile.from_tms(tms_x=x, tms_y=y, zoom=zoom)
            b = tile.bounds
            for i in range(2):
                lat = b[i].latitude_longitude[0]
                lon = b[i].latitude_longitude[1]
                south = min(south, -lat)
                north = max(north, -lat)
                east = max(east, lon)
                west = min(west, lon)

    return east, west, north, south


def mask_translate(src_msk_info, trgt_msk_info):
    '''
    MASK_TRANSLATE translates mask from one tile set to the other.
    
    :param src_msk_info:
        Source mask information given as a tuple (mask, x_min, y_min, zoom).
    :type src_msk_info:
        tuple
    :param trgt_msk_info:
        Target mask information given as a tuple (mask, x_min, y_min, zoom).
    :type trgt_msk_info:
        tuple
    
    :returns:
        Target mask.
    
    NOTE: it is assumed that mask is without border.
    '''

    #    tile_size = 256

    s_msk = src_msk_info[0]
    s_xmin = src_msk_info[1]
    s_ymin = src_msk_info[2]
    s_zoom = src_msk_info[3]
    s_h, s_w = s_msk.shape[:2]

    t_msk = trgt_msk_info[0]
    t_xmin = trgt_msk_info[1]
    t_ymin = trgt_msk_info[2]
    t_zoom = trgt_msk_info[3]
    t_h, t_w = t_msk.shape[:2]
    #    t_xmax += t_w / tile_size  -  1
    #    t_ymax += h_w / tile_size  -  1

    mask = np.zeros((t_h, t_w), np.uint8)

    for i in range(0, s_h):
        for j in range(0, s_w):
            if s_msk[i][j] > 0:
                lonlat = imagepixels2lonlat([(j, i)], s_xmin, s_ymin, zoom=s_zoom)
                pt = lonlat2imagepixels(lonlat, t_xmin, t_ymin, zoom=t_zoom)[0]
                if pt[0] >= 0 and pt[0] < t_w and pt[1] >= 0 and pt[1] < t_h:
                    mask[pt[1]][pt[0]] = s_msk[i][j]

    return mask


def poly2lonlat(polybnd, xt_min, yt_min, zoom=13):
    '''
    POLY2LONLAT translates a polygon to external and internal boundaries
    lat/lon pairs with respect to the given tile coordinates and zoom level.
    
    :param polybnd:
        Polygon described by its external and internal boundaries.
    :type polybnd:
        shapely.geometry.Polygon
    :param xt_min:
        Minimum x index for the tile.
    :type xt_min:
        int
    :param xt_max:
        Maximum x index for the tile.
    :type xt_max:
        int
    :param yt_min:
        Minimum y index for the tile.
    :type yt_min:
        int
    :param yt_max:
        Maximum y index for the tile.
    :type yt_max:
        int
    :param zoom:
        Zoom level.
    
    :returns:
        List of tuples (A, B):
           A = List of (lon, lat) pairs representing the external boundary of the polygon;
           B = List of lists of (lon, lat) pairs representing its internal boundaries.
    '''

    if polybnd.geom_type == "MultiPolygon":
        polygons = polybnd.geoms
    else:
        polygons = [polybnd]

    multi_poly = []

    for poly in polygons:
        # process exterior boundary
        external_boundary = []
        pixels = []
        for pt in poly.exterior.coords:
            pixels.append((pt[0], pt[1]))
        external_boundary = imagepixels2lonlat(pixels, xt_min, yt_min, zoom=zoom)

        # process interior boundaries
        internal_boundaries = []
        for intr in poly.interiors:
            pixels = []
            for pt in intr.coords:
                pixels.append((pt[0], pt[1]))
            internal_boundaries.append(imagepixels2lonlat(pixels, xt_min, yt_min, zoom=zoom))

        multi_poly.append((external_boundary, internal_boundaries))

    return multi_poly


def multipoly2kml(multi_poly, seed_lonlat=None, kml_name=None):
    '''
    POLY2KML generates KML for a geo polygon specified by its external and
    internal boundaries.
    
    :param multi_poly:
        List of tuples (A, B):
           A = List of (lon, lat) pairs representing the external boundary of the polygon;
           B = List of lists of (lon, lat) pairs representing its internal boundaries.
    :type multi_poly:
        list
    :param seed_lonlat:
        Geo location that was used for computation of the polygon (optional).
    :type:
        tuple (lon, lat)
    :param kml_name:
        Name of the KML file, where the polygon should be saved.
        If kml_name == None, then the KML code is written to stdout.
    :type kml_name:
        string
    '''

    kml = simplekml.Kml()
    kml.document.name = "Estimated polygon"

    for poly in multi_poly:
        external_boundary = poly[0]
        internal_boundaries = poly[1]
        pol = kml.newpolygon(name="My polygon",
                             outerboundaryis=external_boundary,
                             innerboundaryis=internal_boundaries)
        pol.style.polystyle.color = simplekml.Color.changealphaint(100, simplekml.Color.blue)

    if seed_lonlat != None:
        kml.newpoint(name="Seed location", coords=seed_lonlat)

    if kml_name == None:
        print(kml.kml())
    else:
        kml.save(kml_name)

    return


# ==============================================================================
# Main function.
# ==============================================================================
def main(argv):
    # print(__doc__)

    lat = 47.24329998
    lon = -97.66187402
    zoom = 19

    #x_min, x_max, y_min, y_max = bbox2tiles(lon, lat, zoom=zoom)
    east = -121.95883665742659
    west = -121.96235927124407
    north = 37.288440939723365
    south = 37.285635060276626

    x_min, x_max, y_min, y_max = x2tiles(east, west, north, south, zoom=zoom)
    print("Boundaries:", x_min, x_max, y_min, y_max)
    print(east, west, north, south)
    east, west, north, south = x2bbox(x_min, x_max, y_min, y_max, zoom=zoom)
    print(east, west, north, south)

    print("west, south", lonlat2tilepixel(west, south, zoom=zoom))
    print("west, north", lonlat2tilepixel(west, north, zoom=zoom))
    print("east, south", lonlat2tilepixel(east, south, zoom=zoom))
    print("east, north", lonlat2tilepixel(east, north, zoom=zoom))

    lst = [(west, south), (west, north), (east, south), (east, north)]
    print(lonlat2imagepixels(lst, x_min, y_min, zoom=zoom))
    sys.exit()
    tiles2image(x_min, x_max, y_min, y_max, zoom=zoom, source="bing", ttype="mapbox.satellite")


    (x, y) = lonlat2imagepixels([(lon, lat)], xt_min=x_min, yt_min=y_min, zoom=zoom)[0]
    print(x, y)

    print(lon, lat)
    (lon, lat) = imagepixels2lonlat([(x, y)], x_min, y_min, zoom=zoom)[0]
    print(lon, lat)

    (x, y) = lonlat2imagepixels([(lon, lat)], xt_min=x_min, yt_min=y_min, zoom=zoom)[0]
    print(x, y)


if __name__ == "__main__":
    main(sys.argv)
