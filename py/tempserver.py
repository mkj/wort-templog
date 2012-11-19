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

        self.fridge = fridge.Fridge()
        self.fridge.run(self)


    def take_readings(self):
        ret = self.readings
        self.readings = []
        return ret

    def pushfront(self, readings):
        """ used if a caller of take_readings() fails """
        self.readings = pushback + self.readings

    def add_reading(self, reading):
        """ adds a reading at the current time """
        self.readings.append( (reading, utils.monotonic_time()))

    def current_temps(self):
        """ returns (wort_temp, fridge_temp, ambient_temp) tuple """
        return current

    def set_current(self, wort, fridge, ambient):
        current = (wort, fridge, ambient)

    def uptime(self):
        return utils.monotonic_time() - self.start_time()

    def now(self):
        return utils.monotonic_time()

def spawn_timer(seconds, fn, *args, **kwargs):
    def loop():
        while True:
            fn(*args, **kwargs)
            gevent.sleep(seconds)
    return gevent.spawn(loop)

def setup():
    pass

def main():
    setup()

    def p(x):
        print "hello %s" % x

    spawn_timer(2, p, 'one')

    gevent.sleep(20)


if __name__ == '__main__':
    main()
