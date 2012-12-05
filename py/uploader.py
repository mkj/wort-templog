import config

import json
import hmac
import zlib

class Uploader(gevent.Greenlet):
    def __init__(self, server):
        gevent.Greenlet.__init__(self)
        self.server = server

    def _run(self):
        while True:
            self.do()
            gevent.sleep(config.UPLOAD_SLEEP)

    def get_tosend(self, readings):
        tosend = {}

        tosend['fridge_on'] = self.server.fridge.is_on()

        tosend['now'] = self.server.now()
        tosend['readings'] = readings

        tosend['wort_name'] = self.server.wort_name
        tosend['fridge_name'] = self.server.wort_fridge_name

        tosend.update(dict(self.server.params))

        tosend['start_time'] = self.server.start_time
        tosend['uptime'] = utils.uptime()

        return tosend

    def send(self, tosend):
        js = json.dumps(tosend)
        js_enc = binascii.b2a_base64(zlib.compress(js))
        mac = hmac.new(config.HMAC_KEY, js_enc).hexdigest()
        url_data = urllib.urlencode( {'data': js_enc, 'hmac': mac} )
        con = urllib2.urlopen(config.UPDATE_URL, url_data)
        result = con.read(100)
        if result != 'OK':
            raise Exception("Server returned %s" % result)

    def do():
        readings = self.server.take_readings()
        try:
            tosend = self.get_tosend(readings)
            readings = None
            self.send(tosend)
        except Exception, e:
            EX"Error in uploader: %s" % str(e))
        finally:
            if readings is not None:
                self.server.pushfront(readings)
