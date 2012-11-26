#!/usr/bin/env python2.7

import sys
import os
import gevent

import utils

class Tempserver(object):
    def __init__(self):
        self.readings = []
        self.current = (None, None, None)

        self.start_time = utils.monotonic_time()

        self.fridge = fridge.Fridge(self)
        self.fridge.start()

        self.set_sensors(sensor_ds18b20.DS18B20s(self))

    def set_sensors(self, sensors):
        if self.hasattr(self, 'sensors'):
            self.sensors.kill()
        self.sensors = sensors
        self.wort_name = sensors.wort_name()
        self.fridge_name = sensors.fridge_name()
        self.sensor_names = sensors.sensor_names()

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
        self.readings.append( (reading, utils.monotonic_time()))
        self.current = (reading.get(self.wort_name, None),
                    reading.get(self.fridge_name, None))

    def current_temps(self):
        """ returns (wort_temp, fridge_temp) tuple """
        return current
