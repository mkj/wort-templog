#!/usr/bin/env python2.7

import binascii
import json
import hmac
import zlib
from datetime import datetime, timedelta
import time
import urllib
import sys
import os
import traceback
import fcntl

import bottle
from bottle import route, request, response

import config
import log
import secure

DATE_FORMAT = '%Y%m%d-%H.%M'
ZOOM_SCALE = 2.0

@route('/update', method='post')
def update():
    js_enc = request.forms.data
    mac = request.forms.hmac

    if hmac.new(config.HMAC_KEY, js_enc).hexdigest() != mac:
        raise bottle.HTTPError(code = 403, output = "Bad key")

    js = zlib.decompress(binascii.a2b_base64(js_enc))

    params = json.loads(js)

    log.parse(params)

    return "OK"

@route('/graph.png')
def graph():
    length_minutes = int(request.query.length)
    end = datetime.strptime(request.query.end, DATE_FORMAT)
    start = end - timedelta(minutes=length_minutes)

    response.set_header('Content-Type', 'image/png')
    start_epoch = time.mktime(start.timetuple())
    return log.graph_png(start_epoch, length_minutes * 60)

@route('/set/update', method='post')
def update():
    post_json = json.loads(request.forms.data)

    csrf_blob = post_json['csrf_blob']

    return str(post_json['params'])

@route('/set')
def set():
    allowed = ["false", "true"][secure.get_user_hash() in config.ALLOWED_USERS]
    return bottle.template('set', 
        inline_data = log.get_params(), 
        csrf_blob = secure.get_csrf_blob(),
        allowed = allowed)

@route('/set_current.json')
def set_fresh():
    response.set_header('Content-Type', 'application/javascript')
    return log.get_current()

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

@route('/debug')
def debuglog():
    response.set_header('Content-Type', 'text/plain')
    return log.tail_debug_log()

@route('/env')
def env():
    response.set_header('Content-Type', 'text/plain')
    #return '\n'.join(traceback.format_stack())
    return '\n'.join(("%s %s" % k) for k in  request.environ.items())
    #return str(request.environ)
    #yield "\n"
    #var_lookup = environ['mod_ssl.var_lookup']
    #return var_lookup("SSL_SERVER_I_DN_O")

@bottle.get('/<filename:re:.*\.js>')
def javascripts(filename):
    response.set_header('Cache-Control', "public, max-age=1296000")
    return bottle.static_file(filename, root='static')

secure.setup_csrf()

def main():
    #bottle.debug(True)
    #bottle.run(reloader=True)
    bottle.run(server='cgi', reloader=True)
    #bottle.run(port=9999, reloader=True)

if __name__ == '__main__':
    main()
    

