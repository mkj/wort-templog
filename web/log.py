import rrdtool
import os
import os.path
import sys
import glob
import hashlib
import tempfile
from colorsys import hls_to_rgb

import config

def sensor_rrd_path(s):
    return '%s/sensor_%s.rrd' % (config.DATA_PATH, s)

# returns (path, sensor_name) tuples
def all_sensors():
    return [(r, os.path.basename(r[:-4])) 
        for r in glob.glob('%s/*.rrd' % config.DATA_PATH)]

def create_rrd(sensor_id):
    rrdtool.create(sensor_rrd_path(sensor_id), '-s', '300',
                'DS:temp:GAUGE:600:-10:100',
                'RRA:AVERAGE:0.5:1:1051200')


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
    for n, (rrdfile, sensor) in enumerate(rrds):
        vname = 'temp%d' % n
        graph_args.append('DEF:%(vname)s=%(rrdfile)s:temp:AVERAGE' % locals())
        width = config.LINE_WIDTH
        legend = config.SENSOR_NAMES.get(sensor, sensor)
        colour = config.SENSOR_COLOURS.get(legend, colour_from_string(sensor))
        graph_args.append('LINE%(width)f:%(vname)s#%(colour)s:%(legend)s' % locals())

    tempf = tempfile.NamedTemporaryFile()
    args = [tempf.name, '-s', str(int(start)),
        '-e', str(int(start+length)),
        '-w', str(config.GRAPH_WIDTH),
        '-h', str(config.GRAPH_HEIGHT),
        '--slope-mode',
        '--border', '0',
        '--color', 'BACK#ffffff',
        '--imgformat', 'PNG'] \
        + graph_args
    if config.GRAPH_FONT:
        args += ['--font', 'DEFAULT:0:%s' % config.GRAPH_FONT]
    print>>sys.stderr, args
    rrdtool.graph(*args)
    return tempf.read()

def sensor_update(sensor_id, measurements, first_real_time, time_step):
    try:
        open(sensor_rrd_path(sensor_id))
    except IOError, e:
        create_rrd(sensor_id)

    values = ['%f:%f' % p for p in 
        zip((first_real_time + time_step*t for t in xrange(len(measurements))),
            measurements)]

    rrdfile = sensor_rrd_path(sensor_id)
    rrdtool.update(rrdfile, *values)

    # be paranois
    f = file(rrdfile)
    os.fsync(f.fileno())

def record_debug(lines):
    f = open('%s/debug.log', config.DATA_PATH, 'a+')
    f.write('===== %s =====' % time.strftime('%a, %d %b %Y %H:%M:%S')
    f.writelines(('%s\n' % s for s in lines))
    f.flush()
    return f

def parse(lines):
   
    debugf = record_debug(lines):

    entries = dict(l.split('=', 1) for l in lines)
    if len(entries) != len(lines):
        raise Exception("Keys are not unique")

    num_sensors = int(entries['sensors'])
    num_measurements = int(entries['sensors'])

    sensor_ids = [entries['sensor_id%d' % n] for n in xrange(num_sensors)]

    meas = []
    for s in sensors:
        meas.append([])

    def val_scale(v):
        # convert decidegrees to degrees
        return 0.1 * v

    for n in xrange(num_measurements):
        vals = [val_scale(int(entries["meas%d" % n].strip().split()))]
        if len(vals) != num_sensors:
            raise Exception("Wrong number of sensors for measurement %d" % n)
        # we make an array of values for each sensor
        for s in xrange(num_sensors):
            meas[s].append(vals[s])

    avr_now = float(entries['now'])
    avr_first_time = float(entries['first_time'])
    time_step = float(entries['time_step'])

    first_real_time = time.time() - (avr_now - avr_first_time)

    for sensor_id, measurements in zip(sensors, meas):
        sensor_update(sensor_id, measurements, first_real_time, time_step)

    debugf.write("Updated %d sensors\n" % len(sensors)
    debugf.flush()
