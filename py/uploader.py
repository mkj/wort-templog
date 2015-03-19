import json
import hmac
import zlib
import binascii
import logging

import gevent
import requests

import config
from utils import L,D,EX,W,E
import utils

class Uploader(gevent.Greenlet):
    def __init__(self, server):
        gevent.Greenlet.__init__(self)
        self.server = server

        requests_log = logging.getLogger("requests")
        requests_log.setLevel(logging.WARNING)

    def _run(self):
        gevent.sleep(5)
        while True:
            self.do()
            self.server.sleep(config.UPLOAD_SLEEP)

    def get_tosend(self, readings):
        tosend = {}

        tosend['fridge_on'] = self.server.fridge.is_on()

        tosend['now'] = self.server.now()
        tosend['readings'] = readings

        tosend['wort_name'] = self.server.wort_name
        tosend['fridge_name'] = self.server.wort_name

        tosend['current_params'] = dict(self.server.params)

        tosend['start_time'] = self.server.start_time
        tosend['uptime'] = utils.uptime()

        return tosend

    def send(self, tosend):
        js = json.dumps(tosend)
        js_enc = binascii.b2a_base64(zlib.compress(js))
        mac = hmac.new(config.HMAC_KEY, js_enc).hexdigest()
        send_data = {'data': js_enc, 'hmac': mac}
        r = requests.post(config.UPDATE_URL, data=send_data, timeout=60)
        result = r.text
        if result != 'OK':
            raise Exception("Server returned %s" % result)

    def do(self):
        readings = self.server.take_readings()
        try:
            tosend = self.get_tosend(readings)
            nreadings = len(readings)
            self.send(tosend)
            readings = None
            D("Sent updated %d readings" % nreadings)
        except requests.exceptions.RequestException, e:
            E("Error in uploader: %s" % str(e))
        except Exception, e:
            EX("Error in uploader: %s" % str(e))
        finally:
            if readings is not None:
                self.server.pushfront(readings)
