#!/usr/bin/env python2.7

import bottle
from bottle import route, request

@route('/update', method='post')
def update():
    return "Done"

@route('/graph.png')
def graph():
    pass

@route('/')
def top():
    return bottle.template('top', urlparams=request.query_string)

def main():
    bottle.debug(True)
    bottle.run(port=9999, reloader=True)

if __name__ == '__main__':
    main()
    

