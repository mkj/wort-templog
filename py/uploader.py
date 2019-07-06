import json
import hmac
import hashlib
import zlib
import binascii
import logging
import asyncio

import aiohttp

import config
from utils import L,D,EX,W,E
import utils

class Uploader(object):
    def __init__(self, server):
        self.server = server
        self.limitlog = utils.NotTooOften(600)

    @asyncio.coroutine
    def run(self):
        # wait for the first read
        yield from asyncio.sleep(5)
        while True:
            yield from self.do()
            yield from asyncio.sleep(config.UPLOAD_SLEEP)

    def get_tosend(self, readings):
        tosend = {}

        tosend['fridge_on'] = self.server.fridge.is_on()

        tosend['now'] = self.server.now()
        tosend['readings'] = readings

        tosend['wort_name'] = self.server.wort_name
        tosend['fridge_name'] = self.server.wort_name

        tosend['current_params'] = dict(self.server.params)
        tosend['current_params_epoch'] = self.server.params.get_epoch()

        tosend['start_time'] = self.server.start_time
        tosend['uptime'] = utils.uptime()

        return tosend

    class BadServerResponse(Exception):
        pass

    @asyncio.coroutine
    def send(self, tosend):
        js = json.dumps(tosend)
        if self.server.test_mode():
            D("Would upload %s to %s" % (js, config.UPDATE_URL))
            return
        js_enc = binascii.b2a_base64(zlib.compress(js.encode())).strip()
        mac = hmac.new(config.HMAC_KEY.encode(), js_enc, hashlib.sha256).hexdigest()
        send_data = {'data': js_enc.decode(), 'hmac': mac}
        r = yield from asyncio.wait_for(aiohttp.request('post', config.UPDATE_URL, data=send_data), 60)
        result = yield from asyncio.wait_for(r.text(), 60)
        if r.status == 200 and result != 'OK':
            raise BadServerResponse("Server returned %s" % result)

    @asyncio.coroutine
    def do(self):
        try:
            readings = self.server.take_readings()
            tosend = self.get_tosend(readings)
            D("tosend >>>%s<<<" % str(tosend))
            nreadings = len(readings)
            yield from self.send(tosend)
            readings = None
            D("Sent updated %d readings" % nreadings)
        except aiohttp.ClientResponseError as e:
            self.limitlog.log("Error with uploader: %s" % str(e))
        except asyncio.TimeoutError as e:
            self.limitlog.log("uploader http timed out: %s" % str(e))
        except self.BadServerResponse as e:
            self.limitlog.log("Bad reply with uploader: %s" % str(e))
        except Exception as e:
            EX("Error in uploader: %s" % str(e))
        finally:
            if readings is not None:
                self.server.pushfront(readings)
