# -*- coding: utf-8 -*-
import collections
import json
import signal
import io

import config
from utils import W,L,E,EX

_FIELD_DEFAULTS = {
    'fridge_setpoint': 16,
    'fridge_difference': 0.2,
    'overshoot_delay': 720, # 12 minutes
    'overshoot_factor': 1, # ºC
    'disabled': False,
    'nowort': False,
    'fridge_range_lower': 3,
    'fridge_range_upper': 3,
    }

class Params(dict):
    class Error(Exception):
        pass

    def __init__(self):
        self.update(_FIELD_DEFAULTS)

    def __getattr__(self, k):
        return self[k]

    def __setattr__(self, k, v):
        # fail if we set a bad value
        self[k]
        self[k] = v

    def _do_load(self, f):
        try:
            u = json.load(f)
        except Exception as e:
            raise self.Error(e)

        for k in u:
            if k.startswith('_'):
                continue
            if k not in self:
                raise self.Error("Unknown parameter %s=%s in file '%s'" % (str(k), str(u[k]), getattr(f, 'name', '???')))
        self.update(u)

        L("Loaded parameters")
        L(self.save_string())

    def load(self, f = None):
        if f:
            return self._do_load(f)
        else:
            with open(config.PARAMS_FILE, 'r') as f:
                try:
                    return self._do_load(f)
                except IOError as e:
                    W("Missing parameter file, using defaults. %s" % str(e))
                    return

    def _do_save(self, f):
        json.dump(self, f, sort_keys=True, indent=4)
        f.write('\n')
        f.flush()

    def save(self, f = None):
        if f:
            return self._do_save(f)
        else:
            with file(config.PARAMS_FILE, 'w') as f:
                return self._do_save(f)

    def save_string(self):
        s = io.StringIO()
        self.save(s)
        return s.getvalue()
