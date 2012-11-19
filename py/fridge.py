from utils import L,W,E
import config

class Fridge(object):
    def __init__(self):
        self.setup_gpio()
        self.wort_valid_clock = 0

    def setup_gpio(self):
        fn = '%s/direction' % config.FRIDGE_GPIO
        f = open(fn, 'w')
        f.write('low')
        f.close()
        # .off() shouldn't do anything, but tests that "value" is writable
        self.off()

    def turn(self, value):
        fn = '%s/value' % config.FRIDGE_GPIO
        f = open(fn, 'w')
        if value:
            f.write('1')
        else:
            f.write('0')
        f.close()

    def on(self):
        self.turn(1)

    def off(self):
        self.turn(0)

    def do(self):
        wort, fridge, ambient = server.current_temps()

        if server.uptime() < config.FRIDGE_DELAY:
            L("fridge skipping, too early")
            return

        # handle broken wort sensor
        if wort is not None:
            self.wort_valid_clock = server.now()
        else:
            W("Invalid wort sensor")
            invalid_time = server.now() - self.wort_valid_clock
            if invalid_time < config.FRIDGE_WORT_INVALID_TIME:
                W("Has only been invalid for %d, waiting" % invalid_time)
                return

        if fridge is None:
            W("Invalid fridge sensor")

        

        

        

    def run(self, server):
        self.server = server

        while True:
            self.do()
            gevent.sleep(config.FRIDGE_SLEEP)
