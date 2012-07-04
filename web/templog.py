#!/usr/bin/env python2.7

import binascii
import hmac
import zlib
from datetime import datetime, timedelta
import time
import urllib
import sys

import bottle
from bottle import route, request, response

import config
import log

DATE_FORMAT = '%Y%m%d-%H.%M'
ZOOM_SCALE = 2.0

@route('/update', method='post')
def update():
    enc_lines = request.forms.lines
    mac = request.forms.hmac

    if hmac.new(config.HMAC_KEY, enc_lines).hexdigest() != mac:
        raise HTTPError(code = 403, output = "Bad key")

    lines = zlib.decompress(binascii.a2b_base64(enc_lines)).split('\n')

    log.parse(lines)

    return "OK"

@route('/graph.png')
def graph():
    length_minutes = int(request.query.length)
    end = datetime.strptime(request.query.end, DATE_FORMAT)
    start = end - timedelta(minutes=length_minutes)

    response.set_header('Content-Type', 'image/png')
    start_epoch = time.mktime(start.timetuple())
    return log.graph_png(start_epoch, length_minutes * 60)

@route('/')
def top():

    minutes = int(request.query.get('length', 26*60))

    if 'end' in request.query:
        end = datetime.strptime(request.query.end, DATE_FORMAT)
    else:
        end = datetime.now()

    if 'zoom' in request.query:
        orig_start = end - timedelta(minutes=minutes)
        orig_end = end
        xpos = int(request.query.x)
        xpos -= config.GRAPH_LEFT_MARGIN * config.ZOOM

        if xpos >= 0 and xpos < config.GRAPH_WIDTH * config.ZOOM:
            click_time = orig_start \
                + timedelta(minutes=(float(xpos) / (config.GRAPH_WIDTH * config.ZOOM)) * minutes)
            minutes = int(minutes / ZOOM_SCALE)

            end = click_time + timedelta(minutes=minutes/2)
        else:
            # zoom out
            minutes = int(minutes*ZOOM_SCALE)
            end += timedelta(minutes=minutes/2)

    if end > datetime.now():
        end = datetime.now()
        
    request.query.replace('length', minutes)
    request.query.replace('end', end.strftime(DATE_FORMAT))

    urlparams = urllib.urlencode(request.query)
    return bottle.template('top', urlparams=urlparams,
                    end = end.strftime(DATE_FORMAT),
                    length = minutes)

@route('/test')
def test():
    import config
    import os
    f = open('%s/testout' % config.DATA_PATH, 'a+')
    f.write("more")
    f.flush()
    f.close()

    return 'done'

def main():
    #bottle.debug(True)
    #bottle.run(reloader=True)
    bottle.run(server='cgi', reloader=True)
    #bottle.run(port=9999, reloader=True)

if __name__ == '__main__':
    main()
    

