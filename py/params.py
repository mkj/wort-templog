# -*- coding: utf-8 -*-
import collections
import json
import signal
import StringIO

import gevent

import config
from utils import W,L,E,EX

_FIELD_DEFAULTS = {
    'fridge_setpoint': 16,
    'fridge_difference': 0.2,
    'overshoot_delay': 720, # 12 minutes
    'overshoot_factor': 1, # ºC
    'disabled': False,
    }

class Params(dict):
    class Error(Exception):
        pass

    def __init__(self):
        self.update(_FIELD_DEFAULTS)
        gevent.signal(signal.SIGHUP, self.reload_signal)

    def __getattr__(self, k):
        return self[k]

    def __setattr__(self, k, v):
        # fail if we set a bad value
        self[k]
        self[k] = v

    def load(self, f = None):
        if not f:
            try:
                f = file(config.PARAMS_FILE, 'r')
            except IOError, e:
                W("Missing parameter file, using defaults. %s", e)
                return
        try:
            u = json.load(f)
        except Exception, e:
            raise self.Error(e)

        for k in u:
            if k not in self:
                raise self.Error("Unknown parameter %s=%s in file '%s'" % (str(k), str(u[k]), getattr(f, 'name', '???')))
        self.update(u)

        L("Loaded parameters")
        L(self.save_string())


    def save(self, f = None):
        if not f:
            f = file(config.PARAMS_FILE, 'w')
        json.dump(self, f, sort_keys=True, indent=4)
        f.write('\n')
        f.flush()

    def save_string(self):
        s = StringIO.StringIO()
        self.save(s)
        return s.getvalue()

    def reload_signal(self):
        try:
            self.load()
            L("Reloaded.")
        except self.Error, e:
            W("Problem reloading: %s" % str(e))
