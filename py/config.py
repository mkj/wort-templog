import os.path

FRIDGE_SLEEP = 60 # this value works. may affect the algorithm
SENSOR_SLEEP = 15 # same for this.
UPLOAD_SLEEP = 83 # nice and prime

FRIDGE_DELAY = 600 # 10 mins, to avoid fridge damage from frequent cycling off/on
FRIDGE_WORT_INVALID_TIME = 300 # 5 mins

# 12 hours of "offline" readings stored
MAX_READINGS = 12*60*60 / SENSOR_SLEEP

PARAMS_FILE = os.path.join(os.path.dirname(__file__), 'tempserver.conf')

SENSOR_BASE_DIR = '/sys/devices/w1_bus_master1'
FRIDGE_GPIO_PIN = 17
WORT_NAME = '28-0000042cf4dd'
FRIDGE_NAME = '28-0000042cccc4'
AMBIENT_NAME = '28-0000042c6dbb'
INTERNAL_TEMPERATURE = '/sys/class/thermal/thermal_zone0/temp'

HMAC_KEY = "a key"
SERVER_URL = 'https://evil.ucc.asn.au/~matt/templog'
UPDATE_URL = "%s/update" % SERVER_URL
SETTINGS_URL = "%s/get_settings" % SERVER_URL

# site-local values overridden in localconfig, eg WORT_NAME, HMAC_KEY
try:
    from localconfig import *
except ImportError:
    pass
