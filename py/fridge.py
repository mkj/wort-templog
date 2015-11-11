# -*- coding: utf-8 -*-
import asyncio

from utils import L,W,E,EX,D
import config

import gpio
import utils

class Fridge(object):

    OVERSHOOT_MAX_DIV = 1800.0 # 30 mins

    def __init__(self, server, nowait = False):
        self.server = server
        self.gpio = gpio.Gpio(config.FRIDGE_GPIO_PIN, "fridge")
        self.integrator = utils.StepIntegrator(self.server.now, self.server.params.overshoot_delay)
        self.wort_valid_clock = 0
        self.fridge_on_clock = 0
        self.off()
        if nowait:
            self.fridge_off_clock = 0

    def turn(self, value):
        self.gpio.turn(value)
        self.integrator.turn(value)

    def on(self):
        self.turn(True)

    def off(self):
        self.turn(False)
        self.fridge_off_clock = self.server.now()

    def is_on(self):
        return self.gpio.get_state()

    @asyncio.coroutine
    def run(self):
        if self.server.params.disabled:
            L("Fridge is disabled")
        while True:
            try:
                self.do()
                yield from self.server.sleep(config.FRIDGE_SLEEP)
            except Exception as e:
                EX("fridge failed")

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

        self.integrator.set_limit(params.overshoot_delay)

        # Safety to avoid bad things happening to the fridge motor (?)
        # When it turns off don't start up again for at least FRIDGE_DELAY
        if not self.is_on() and off_time < config.FRIDGE_DELAY:
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

        D("fridge on %s" % self.is_on())

        if self.is_on():
            turn_off = False
            on_percent = self.integrator.integrate() / params.overshoot_delay

            overshoot = params.overshoot_factor * on_percent
            D("on_time %(on_percent)f, overshoot %(overshoot)f" % locals())

            if not params.nowort and wort is not None:
                if wort - overshoot < params.fridge_setpoint:
                    max_div = self.OVERSHOOT_MAX_DIV
                    overshoot_factor = params.overshoot_factor
                    L("wort has cooled enough, %(wort)fº (overshoot %(overshoot)fº = %(overshoot_factor)f * min(%(on_time)f) / %(max_div)f)" % locals() )
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
            D("fridge %(fridge)s max %(fridge_max)s wort %(wort)s wort_max %(wort_max)s" % locals())
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
