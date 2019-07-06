# for server
BTADDR = "00:12:03:27:70:88"
SLEEP_TIME = 60
SERIAL_HOST='home.example.com'
SERIAL_PORT=1999


DATA_PATH = '/home/matt/templog/web/data'

# local config items
HMAC_KEY = 'a hmac key' 
ALLOWED_USERS = [] # list of hashes allowed, as provided by the Email link

UPDATE_URL = 'http://evil.ucc.asn.au/~matt/templog/update'

EMAIL = "test@example.com"

GRAPH_WIDTH = 600
GRAPH_HEIGHT = 700
ZOOM = 1
# determine by viewing the image
GRAPH_LEFT_MARGIN = 65

LINE_WIDTH = 2

SENSOR_NAMES = {
    'sensor_28 CE B2 1A 03 00 00 99': "Old Fridge",
    'sensor_28 CC C1 1A 03 00 00 D4': "Old Ambient",
    'sensor_28 49 BC 1A 03 00 00 54': "Old Wort",
    'sensor_voltage': 'Voltage',
    'sensor_fridge_setpoint': 'Setpoint',
    'sensor_fridge_on': 'Cool',
    'sensor_28-0000042cf4dd': "New Old Wort",
    'sensor_28-0000042d36cc': "Wort",
    'sensor_28-0000042cccc4': "OldFridge",
    'sensor_28-0000042c6dbb': "New Old Fridge",
    'sensor_28-0000068922df': "Fridge",
    'sensor_internal': "Processor",
    }

# print legend for these ones
LEGEND_NAMES = set(("Wort", "Fridge", "Ambient", "Setpoint"))

SENSOR_COLOURS = {'Wort': 'e49222', 
                'Ambient': '028b3d',
                'Voltage': '7db5d3aa',
                'Fridge': '93c8ff',
                'Setpoint': '39c662',
                'Cool': 'd7cedd',
                'Processor': 'bf7a69',
                }


GRAPH_FONT = "Prociono"
#GRAPH_FONT = "URW Gothic L"


# 1 hour
CSRF_TIMEOUT = 3600

LONG_POLL_TIMEOUT = 500

try:
    from localconfig import *
except ImportError:
    pass
