# for server
BTADDR = "00:12:03:27:70:88"
SLEEP_TIME = 5

DATA_PATH = '/home/matt/templog/web/data'

HMAC_KEY = 'a hmac key' # override in local config file

UPDATE_URL = 'http://evil.ucc.asn.au/~matt/templog/update'

GRAPH_WIDTH = 1200
GRAPH_HEIGHT = 600
ZOOM = 1

LINE_WIDTH = 2

SENSOR_NAMES = {'sensor_28 CE B2 1A 03 00 00 99': "Fridge",
    'sensor_28 CC C1 1A 03 00 00 D4': "Ambient",
    'sensor_28 49 BC 1A 03 00 00 54': "Wort",
    'sensor_voltage': 'Voltage',
    'sensor_fridge_setpoint': 'Setpoint',
    'sensor_fridge_on': 'Cool',
    }

SENSOR_COLOURS = {'Wort': 'e49222', 
                'Ambient': '028b3d',
                'Voltage': '7db5d3aa',
                'Fridge': '4c40c8',
                'Setpoint': '39c662',
                'Cool': 'd7cedd',
                }


GRAPH_FONT = "Prociono"
#GRAPH_FONT = "URW Gothic L"

# determine by zooming in an image viewer
GRAPH_LEFT_MARGIN = 63

try:
    from localconfig import *
except ImportError:
    pass
