#!/home/matt/templog/venv/bin/python

import sys
import os
import gevent
import gevent.monkey

import utils
import fridge
import config
import sensor_ds18b20
import params


class Tempserver(object):
    def __init__(self):
        self.readings = []
        self.current = (None, None)

        # don't patch os, fork() is used by daemonize
        gevent.monkey.patch_all(os=False, thread=False)

        self.start_time = self.now()

        self.params = params.Params()
        self.params.load()

        self.fridge = fridge.Fridge(self)
        self.fridge.start()

        self.set_sensors(sensor_ds18b20.DS18B20s(self))

    def run(self):
        # won't return.
        while True:
            gevent.sleep(60)

    def now(self):
        return utils.monotonic_time()

    def set_sensors(self, sensors):
        if hasattr(self, 'sensors'):
            self.sensors.kill()
        self.sensors = sensors
        self.wort_name = sensors.wort_name()
        self.fridge_name = sensors.fridge_name()

    def take_readings(self):
        ret = self.readings
        self.readings = []
        return ret

    def pushfront(self, readings):
        """ used if a caller of take_readings() fails """
        self.readings = pushback + self.readings

    # a reading is a map of {sensorname: value}. temperatures
    # are float degrees
    def add_reading(self, reading):
        """ adds a reading at the current time """
        self.readings.append( (reading, self.now()))
        self.current = (reading.get(self.wort_name, None),
                    reading.get(self.fridge_name, None))

    def current_temps(self):
        """ returns (wort_temp, fridge_temp) tuple """
        return self.current

def setup_logging():
    logging.basicConfig(format='%(asctime)s %(message)s', 
            datefmt='%m/%d/%Y %I:%M:%S %p',
            level=logging.INFO)

def main():
    server = Tempserver()

    if '--daemon' in sys.argv:
        utils.cheap_daemon()

    server.run()

if __name__ == '__main__':
    main()
