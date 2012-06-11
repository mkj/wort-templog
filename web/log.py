import rrdtool
import os
import sys

import config

def sensor_rrd_path(s):
    return '%s/sensor_%s.rrd' % (config.DATA_PATH, s)

def create_rrd(sensor_id):
    rrdtool.create(sensor_rrd_path(sensor_id), '-s', '300',
                'DS:temp:GAUGE:600:-10:100',
                'RRA:AVERAGE:0.5:1:1051200')

def sensor_update(sensor_id, measurements, first_real_time, time_step):
    try:
        open(sensor_rrd_path(sensor_id))
    except IOError, e:
        create_rrd(sensor_id)

    value_text = ' '.join('%f:%f' % p for p in 
        zip(measurements, 
        (first_real_time + time_step*t for t in xrange(len(measurements)))))

    rrdtool.update(sensor_rrd_path(sensor_id), value_text)

def parse(lines):
    entries = dict(l.split('=', 1) for l in lines)
    if len(entries) != len(lines);
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

    avr_now = float(entries['now')
    avr_first_time = float(entries['first_time'])
    time_step = float(entries['time_step'])

    first_real_time = time.time() - (avr_now - avr_first_time)

    for sensor_id, measurements in zip(sensors, meas):
        sensor_update(sensor_id, measurements, first_real_time, time_step)
