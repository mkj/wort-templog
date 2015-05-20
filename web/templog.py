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
import hashlib

import bottle
from bottle import route, request, response

import config
import log
import secure
import atomicfile

DATE_FORMAT = '%Y%m%d-%H.%M'
ZOOM_SCALE = 2.0

class TemplogBottle(bottle.Bottle):
    def run(*args, **argm):
        argm['server'] = 'gevent'
        super(TemplogBottle, self).run(*args, **argm)
        print "ran custom bottle"

#bottle.default_app.push(TemplogBottle())

secure.setup_csrf()

@route('/update', method='post')
def update():
    js_enc = request.forms.data
    mac = request.forms.hmac

    h = hmac.new(config.HMAC_KEY, js_enc.strip(), hashlib.sha256).hexdigest()
    if h != mac:
        raise bottle.HTTPError(code = 403, output = "Bad key")

    js = zlib.decompress(binascii.a2b_base64(js_enc))

    params = json.loads(js)

    log.parse(params)

    return "OK"

def make_graph(length, end):
    length_minutes = int(length)
    end = datetime.strptime(end, DATE_FORMAT)
    start = end - timedelta(minutes=length_minutes)

    start_epoch = time.mktime(start.timetuple())
    return log.graph_png(start_epoch, length_minutes * 60)

def encode_data(data, mimetype):
    return 'data:%s;base64,%s' % (mimetype, binascii.b2a_base64(data).rstrip())


@route('/graph.png')
def graph():
    response.set_header('Content-Type', 'image/png')
    return make_graph(request.query.length, request.query.end)

@route('/set/update', method='post')
def set_update():
    post_json = json.loads(request.forms.data)

    csrf_blob = post_json['csrf_blob']

    if not secure.check_csrf_blob(csrf_blob):
        bottle.response.status = 403
        return "Bad csrf"

    ret = log.update_params(post_json['params'])
    if not ret is True:
        bottle.response.status = 403
        return ret
        
    return "Good"

@route('/set')
def set():
    allowed = ["false", "true"][secure.check_user_hash(config.ALLOWED_USERS)]
    response.set_header('Cache-Control', 'no-cache')
    return bottle.template('set', 
        inline_data = log.get_params(), 
        csrf_blob = secure.get_csrf_blob(),
        allowed = allowed)

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
    graphdata = encode_data(make_graph(request.query.length, request.query.end), 'image/png')
    return bottle.template('top', urlparams=urlparams,
                    end = end.strftime(DATE_FORMAT),
                    length = minutes,
                    graphwidth = config.GRAPH_WIDTH,
                    graphdata = graphdata)

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

def main():
    #bottle.debug(True)
    #bottle.run(reloader=True)
    bottle.run(server='cgi', reloader=True)
    #bottle.run(port=9999, reloader=True)

if __name__ == '__main__':
    main()
    
