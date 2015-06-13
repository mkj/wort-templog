import asyncio
import datetime

import aiohttp

import utils
from utils import L,D,EX,W,E
import config

class ConfigWaiter(object):
    """ Waits for config updates from the server. http long polling """

    def __init__(self, server):
        self.server = server
        self.epoch_tag = None
        self.http_session = aiohttp.ClientSession()
        self.limitlog = utils.NotTooOften(datetime.timedelta(minutes=15))

    @asyncio.coroutine
    def run(self):
        # wait until someting has been uploaded (the uploader itself waits 5 seconds)
        yield from asyncio.sleep(10)
        while True:
            yield from self.do()

            # avoid spinning too fast
            yield from asyncio.sleep(1)

    @asyncio.coroutine
    def do(self):
        try:
            if self.epoch_tag:
                headers = {'etag': self.epoch_tag}
            else:
                headers = None

            r = yield from asyncio.wait_for(
                self.http_session.get(config.SETTINGS_URL, headers=headers), 
                300)
            D("waiter status %d" % r.status)
            if r.status == 200:
                rawresp = yield from asyncio.wait_for(r.text(), 600)

                resp = utils.json_load_round_float(rawresp)

                self.epoch_tag = resp['epoch_tag']
                D("waiter got epoch tag %s" % self.epoch_tag)
                epoch = self.epoch_tag.split('-')[0]
                if self.server.params.receive(resp['params'], epoch):
                    self.server.reload_signal(True)
            elif r.status == 304:
                pass
            else:
                # longer timeout to avoid spinning
                text = yield from asyncio.wait_for(r.text(), 600)
                D("Bad server response. %d %s" % (r.status, text))
                yield from asyncio.sleep(30)

        except aiohttp.errors.ClientError as e:
            self.limitlog.log("Error with configwaiter: %s" % str(e))
        except asyncio.TimeoutError as e:
            self.limitlog.log("configwaiter http timed out: %s" % str(e))
        except Exception as e:
            EX("Error watching config: %s" % str(e))
