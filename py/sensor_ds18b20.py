#!/usr/bin/env python2.7

class DS18B20s(object):

    def __init__(self):
        # query the bus 
        pass

    def get_sensors(self):
        """ Returns a sequence of sensorname """
        pass

    def read(self):
        """ Returns a map of sensorname->temperature """
        pass

    def wort_name(self):
        pass

    def fridge_name(self):
        pass
