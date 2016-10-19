import re
import pokemon_pb2
from utils import f2i
from geopy.geocoders import GoogleV3

default_step = 0.001

class Location(object):
    def __init__(self, location):
        geolocator = GoogleV3()
        prog = re.compile('^(\-?\d+(\.\d+)?),\s*(\-?\d+(\.\d+)?)$')
        if prog.match(location):
            self.origin_lat, self.origin_lon = [float(x) for x in location.split(",")]
            self.alt = 0
        else:
            loc = geolocator.geocode(location_name)
            self.origin_lat, self.origin_lon = loc.latitude, loc.longitude
            self.origin_alt = loc.altitude

        print('[!] lat/long/alt: {} {} {}'.format(local_lat, local_lng, alt))
        self.coord_lat = None
        self.coord_lon = None
        self.coord_alt = None
        self.set_loc_coord(local_lat, local_lng, alt)

    def set_loc_coord(self, lat, lon, alt):
        self.origin_lat = lat
        self.origin_lon = lon
        self.origin_alt = alt
        self.coord_lat = f2i(lat)  # 0x4042bd7c00000000 # f2i(lat)
        self.coord_lon = f2i(lon)  # 0xc05e8aae40000000 #f2i(long)
        self.coord_alt = f2i(alt)

    def get_location_coords():
        return (self.coord_lat, self.coord_lon, self.coord_alt,)

    def bearing(self, lat, lon):
        pass

    def steps(self, steplimit=default_step):
        pos = 1
        x = 0
        y = 0
        dx = 0
        dy = -1
        steplimit2 = steplimit**2
        for step in range(steplimit2):
            debug('looping: step {} of {}'.format((step+1), steplimit**2))
            # Scan location math
            if -steplimit2 / 2 < x <= steplimit2 / 2 and -steplimit2 / 2 < y <= steplimit2 / 2:
                yield (x * 0.0025 + origin_lat, y * 0.0025 + origin_lon,)
            if x == y or x < 0 and x == -y or x > 0 and x == 1 - y:
                (dx, dy) = (-dy, dx)

            (x, y) = (x + dx, y + dy)
