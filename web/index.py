#!/usr/bin/env python2.7

import binascii
import hmac
import zlib

import bottle
from bottle import route, request

import config
import log

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
    start_secs = int(request.query.start)
    # url takes time in hours or days
    if 'day' in request.query:
        start_day = datetime.strptime(request.query.day, '%Y%m%d')
        start = time.mktime(start_day.timetuple())
        length = int(request.query.length) * 3600 * 24
    else:
        start_hour = datetime.strptime(request.query.hour, '%Y%m%d%H')
        start = time.mktime(start_hour.timetuple())
        length = int(request.query.length) * 3600

    response.set_header('Content-Type', 'image/png')
    return log.graph_png(start, length)

@route('/')
def top():
    return bottle.template('top', urlparams=request.query_string)

def main():
    bottle.debug(True)
    bottle.run(port=9999, reloader=True)

if __name__ == '__main__':
    main()
    
