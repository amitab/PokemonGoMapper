import argparse
import struct

def parse_unicode(bytestring):
    decoded_string = bytestring.decode(sys.getfilesystemencoding())
    return decoded_string

def get_args()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-a', '--auth-service', type=str.lower, help='Auth Service', default='ptc')
    parser.add_argument('-u', '--username', help='Username', required=True)
    parser.add_argument('-p', '--password', help='Password', required=False)
    parser.add_argument(
        '-l', '--location', type=parse_unicode, help='Location', required=True)
    parser.add_argument('-st', '--steplimit', help='Steps', required=True)
    parser.add_argument(
        '-H',
        '--host',
        help='Set web server listening host',
        default='127.0.0.1')
    parser.add_argument(
        '-P',
        '--port',
        type=int,
        help='Set web server listening port',
        default=5000)
    return parser.parse_args()

def f2i(float):
    return struct.unpack('<Q', struct.pack('<d', float))[0]
