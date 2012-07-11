
# for server
BTADDR = "00:12:03:27:70:88"
SLEEP_TIME = 5

DATA_PATH = '/home/matt/templog/web/data'

HMAC_KEY = 'a hmac key' # override in local config file

UPDATE_URL = 'https://evil.ucc.asn.au/~matt/templog/update'

GRAPH_WIDTH = 1200
GRAPH_HEIGHT = 600
ZOOM = 1

LINE_WIDTH = 2

SENSOR_NAMES = {'sensor_28 CE B2 1A 03 00 00 99': "Wort",
    'sensor_28 CC C1 1A 03 00 00 D4': "Ambient",
    'sensor_28 49 BC 1A 03 00 00 54': "Other",
    'sensor_voltage': 'Voltage',
    }

SENSOR_COLOURS = {'Wort': 'e49222', 
                'Ambient': '028b3d',
                'Voltage': '7db5d3aa',
                'Other': '78000c',
                }


GRAPH_FONT = "Prociono"
#GRAPH_FONT = "URW Gothic L"

# determine by zooming in an image viewer
GRAPH_LEFT_MARGIN = 63

try:
    import localconfig
    g = globals()
    for k in dir(other):
        if k in g:
            g[k] = other.__dict__[k]
except ImportError:
    pass
