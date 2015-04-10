import asyncio

class SensorTest(object):

    def __init__(self, server):
        self.server = server
        
    def kill(self):
        L("Killed SensorTest")

    def make_vals(self):
        def try_read(f, fallback):
            try:
                return open(f, 'r').read()
            except Exception, e:
                return fallback

        vals = {}
        vals[self.wort_name()] = try_read('test_wort.txt', 18)
        vals[self.fridge_name()] = try_read('test_fridge.txt', 20)
        vals['ambient'] = 31.2
        return vals

    def run(self):

        while True:
            yield from asyncio.sleep(1)
            vals = self.make_vals()
            self.server.add_reading(vals)

    def wort_name(self):
        return '28-wortname'

    def fridge_name(self):
        return '28-fridgename'
