#:vim:et:ts=4:sts=4:sw=4:
import rrdtool
import os
import os.path
import sys
import glob
import hashlib
import tempfile
import time
import syslog
import sqlite3
import traceback
import datetime
from colorsys import hls_to_rgb

import config

def sensor_rrd_path(s):
    return '%s/sensor_%s.rrd' % (config.DATA_PATH, s)

# returns (path, sensor_name) tuples
def all_sensors():
    return [(r, os.path.basename(r[:-4])) 
        for r in glob.glob('%s/*.rrd' % config.DATA_PATH)]

def create_rrd(sensor_id):
    # start date of 10 seconds into 1970 is used so that we can
    # update with prior values straight away.
    if 'voltage' in sensor_id:
        args = [ 
                '--step', '3600',
                'DS:temp:GAUGE:7200:1:10',
                'RRA:AVERAGE:0.5:1:87600']
    else:
        args = [
                '--step', '300',
                'DS:temp:GAUGE:600:-10:100',
                'RRA:AVERAGE:0.5:1:1051200']

    rrdtool.create(sensor_rrd_path(sensor_id), 
                '--start', 'now-60d',
                *args)

# stolen from viewmtn, stolen from monotone-viz
def colour_from_string(str):
    def f(off):
        return ord(hashval[off]) / 256.0
    hashval = hashlib.sha1(str).digest()
    hue = f(5)
    li = f(1) * 0.15 + 0.55
    sat = f(2) * 0.5 + .5
    return ''.join(["%.2x" % int(x * 256) for x in hls_to_rgb(hue, li, sat)])

def graph_png(start, length):
    rrds = all_sensors()

    graph_args = []
    have_volts = False
    for n, (rrdfile, sensor) in enumerate(rrds):
        if 'avrtemp' in sensor:
            continue
        if 'voltage' in sensor:
            have_volts = True
            vname = 'scalevolts'
            graph_args.append('DEF:%(vname)s=%(rrdfile)s:temp:AVERAGE:step=3600' % locals())
        else:
            vname = 'temp%d' % n
            graph_args.append('DEF:raw%(vname)s=%(rrdfile)s:temp:AVERAGE' % locals())
            graph_args.append('CDEF:%(vname)s=raw%(vname)s,0.1,*,2,+' % locals())
        width = config.LINE_WIDTH
        legend = config.SENSOR_NAMES.get(sensor, sensor)
        colour = config.SENSOR_COLOURS.get(legend, colour_from_string(sensor))
        graph_args.append('LINE%(width)f:%(vname)s#%(colour)s:%(legend)s' % locals())

    end = int(start+length)
    start = int(start)

    tempf = tempfile.NamedTemporaryFile()
    dateformat = '%H:%M:%S %Y-%m-%d'
    watermark = ("Now %s\t"
                "Start %s\t"
                "End %s" % (
                datetime.datetime.now().strftime(dateformat),
                datetime.datetime.fromtimestamp(start).strftime(dateformat),
                datetime.datetime.fromtimestamp(end).strftime(dateformat) ))

    args = [tempf.name, '-s', str(start),
        '-e', str(end),
        '-w', str(config.GRAPH_WIDTH),
        '-h', str(config.GRAPH_HEIGHT),
        '--slope-mode',
        '--border', '0',
        '--vertical-label', 'Voltage',
        '--y-grid', '0.1:1',
        '--dynamic-labels',
        '--grid-dash', '1:0',
        '--color', 'GRID#00000000',
        '--color', 'MGRID#aaaaaa',
        '--color', 'BACK#ffffff',
        '--disable-rrdtool-tag',
        '--watermark', watermark,
        '--imgformat', 'PNG'] \
        + graph_args
    args += ['--font', 'DEFAULT:12:%s' % config.GRAPH_FONT]
    args += ['--font', 'WATERMARK:10:%s' % config.GRAPH_FONT]
    if have_volts:
        args += ['--right-axis', '10:-20', # matches the scalevolts CDEF above
            '--right-axis-format', '%.2lf',
            '--right-axis-label', 'Temperature']

    rrdtool.graph(*args)
    return tempf.read()

def sensor_update(sensor_id, measurements, first_real_time, time_step):
    try:
        open(sensor_rrd_path(sensor_id))
    except IOError, e:
        create_rrd(sensor_id)

    if measurements:
        values = ['%d:%f' % p for p in 
            zip((first_real_time + time_step*t for t in xrange(len(measurements))),
                measurements)]

        rrdfile = sensor_rrd_path(sensor_id)
        # XXX what to do here when it fails...
        for v in values:
            try:
                rrdtool.update(rrdfile, v)
            except rrdtool.error, e:
                print>>sys.stderr, "Bad rrdtool update '%s'" % v
                traceback.print_exc(file=sys.stderr)

        # be paranoid
        f = file(rrdfile)
        os.fsync(f.fileno())

def record_debug(lines):
    f = open('%s/debug.log' % config.DATA_PATH, 'a+')
    f.write('===== %s =====\n' % time.strftime('%a, %d %b %Y %H:%M:%S'))
    f.writelines(('%s\n' % s for s in lines))
    f.flush()
    return f

def parse(lines):
   
    debugf = record_debug(lines)

    entries = dict(l.split('=', 1) for l in lines)
    if len(entries) != len(lines):
        raise Exception("Keys are not unique")

    num_sensors = int(entries['sensors'])
    num_measurements = int(entries['measurements'])

    sensors = [entries['sensor_id%d' % n] for n in xrange(num_sensors)]

    meas = []
    for s in sensors:
        meas.append([])

    def val_scale(v):
        # convert decidegrees to degrees
        return 0.1 * v

    for n in xrange(num_measurements):
        vals = [val_scale(int(x)) for x in entries["meas%d" % n].strip().split()]
        if len(vals) != num_sensors:
            raise Exception("Wrong number of sensors for measurement %d" % n)
        # we make an array of values for each sensor
        for s in xrange(num_sensors):
            meas[s].append(vals[s])

    avr_now = float(entries['now'])
    avr_first_time = float(entries['first_time'])
    time_step = float(entries['time_step'])

    if 'avrtemp' in entries:
        avrtemp = val_scale(int(entries['avrtemp']))
        sensor_update('avrtemp', [avrtemp], time.time(), 1)

    if 'voltage' in entries:
        voltage = 0.001 * int(entries['voltage'])
        sensor_update('voltage', [voltage], time.time(), 1)

    #sqlite 
    # - time
    # - voltage
    # - boot time

    first_real_time = time.time() - (avr_now - avr_first_time)

    for sensor_id, measurements in zip(sensors, meas):
        # XXX sqlite add
        sensor_update(sensor_id, measurements, first_real_time, time_step)

    debugf.write("Updated %d sensors\n" % len(sensors))
    debugf.flush()
