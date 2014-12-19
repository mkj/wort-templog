# -*- coding: utf-8 -*-
from utils import L,W,E,EX,D
import config
import gevent

class Fridge(gevent.Greenlet):

    OVERSHOOT_MAX_DIV = 1800.0 # 30 mins

    def __init__(self, server):
        gevent.Greenlet.__init__(self)
        self.server = server
        self.setup_gpio()
        self.wort_valid_clock = 0
        self.fridge_on_clock = 0
        self.off()

    def setup_gpio(self):
        dir_fn = '%s/direction' % config.FRIDGE_GPIO
        with open(dir_fn, 'w') as f:
            f.write('low')
        val_fn = '%s/value' % config.FRIDGE_GPIO
        # XXX - Fridge should have __enter__/__exit__, close the file there.
        self.value_file = open(val_fn, 'r+')

    def turn(self, value):
        self.value_file.seek(0)
        if value:
            self.value_file.write('1')
        else:
            self.value_file.write('0')
        self.value_file.flush()

    def on(self):
        self.turn(True)

    def off(self):
        self.turn(False)
        self.fridge_off_clock = self.server.now()

    def is_on(self):
        self.value_file.seek(0)
        buf = self.value_file.read().strip()
        if buf == '0':
            return False
        if buf != '1':
            E("Bad value read from gpio '%s': '%s'" 
                % (self.value_file.name, buf))
        return True

    # greenlet subclassed
    def _run(self):
        if self.server.params.disabled:
            L("Fridge is disabled")
        while True:
            self.do()
            self.server.sleep(config.FRIDGE_SLEEP)

    def do(self):
        """ this is the main fridge control logic """
        wort, fridge = self.server.current_temps()

        params = self.server.params

        fridge_min = params.fridge_setpoint - params.fridge_range_lower
        fridge_max = params.fridge_setpoint + params.fridge_range_upper

        wort_min = params.fridge_setpoint
        wort_max = params.fridge_setpoint + params.fridge_difference

        off_time = self.server.now() - self.fridge_off_clock

        if wort is not None:
            self.wort_valid_clock = self.server.now()

        # Safety to avoid bad things happening to the fridge motor (?)
        # When it turns off don't start up again for at least FRIDGE_DELAY
        if self.is_off() and off_time < config.FRIDGE_DELAY:
            L("fridge skipping, too early")
            return

        if params.disabled:
            if self.is_on():
                L("Disabled, turning fridge off")
                self.off()
            return

        # handle broken wort sensor
        if wort is None:
            invalid_time = self.server.now() - self.wort_valid_clock
            W("Invalid wort sensor for %d secs" % invalid_time)
            if invalid_time < config.FRIDGE_WORT_INVALID_TIME:
                W("Has only been invalid for %d, waiting" % invalid_time)
                return

        if fridge is None:
            W("Invalid fridge sensor")

        if self.is_on():
            turn_off = False
            on_time = self.server.now() - self.fridge_on_clock

            overshoot = 0
            if on_time > params.overshoot_delay:
                overshoot = params.overshoot_factor \
                    * min(self.OVERSHOOT_MAX_DIV, on_time) \
                    / self.OVERSHOOT_MAX_DIV
            D("on_time %(on_time)f, overshoot %(overshoot)f" % locals())

            if not params.nowort and wort is not None:
                if wort - overshoot < params.fridge_setpoint:
                    L("wort has cooled enough, %(wort)f" % locals() )
                    turn_off = True
            elif fridge is not None and fridge < fridge_min:
                    W("fridge off fallback, fridge %(fridge)f, min %(fridge_min)f" % locals())
                    if wort is None:
                        W("wort has been invalid for %d" % (self.server.now() - self.wort_valid_clock))
                    turn_off = True

            if turn_off:
                L("Turning fridge off")
                self.off()

        else:
            # fridge is off
            turn_on = False
            if not params.nowort \
                and wort is not None \
                and wort >= wort_max:
                    L("Wort is too hot %f, max %f" % (wort, wort_max))
                    turn_on = True
            elif fridge is not None and fridge >= fridge_max:
                    W("frdge on fallback, fridge %(fridge)f, max %(fridge_max)f" % locals())
                    turn_on = True

            if turn_on:
                L("Turning fridge on")
                self.on()
                self.fridge_on_clock = self.server.now()
