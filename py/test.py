#!/usr/bin/env python2.7
import StringIO

import unittest
import sensor_ds18b20
import params

class TestSensors(unittest.TestCase):
    def setUp(self):
        self.sensors = sensor_ds18b20.DS18B20s(None)

    def test_sensors_regex(self):
        f1 = """6e 01 4b 46 7f ff 02 10 71 : crc=71 YES
6e 01 4b 46 7f ff 02 10 71 t=22875
"""
        val = self.sensors.do_sensor('blank', f1)
        self.assertEqual(val, 22.875)

        f2 = """6e 01 4b 46 7f ff 02 10 71 : crc=71 NO
6e 01 4b 46 7f ff 02 10 71 t=22875
"""
        val = self.sensors.do_sensor('blank', f2)
        self.assertEqual(val, None)

        f3 = """6e 01 4b 46 7f ff 02 10 71 : crc=71 YES
6e 01 4b 46 7f ff 02 10 71 t=-1
"""
        val = self.sensors.do_sensor('blank', f3)
        self.assertEqual(val, -0.001)

class TestParams(unittest.TestCase):
    def setUp(self):
        self.params = params.Params()

    def test_params_basic(self):
        defparams = params.Params()
        self.assertEqual(defparams.overshoot_factor, 
            params._FIELD_DEFAULTS['overshoot_factor'])

        # fetching a bad parameter fails
        with self.assertRaises(KeyError):
            x = self.params.param_that_doesnt_exist

        # setting a parameter
        defparams.overshoot_factor = 8877
        self.assertEqual(defparams.overshoot_factor, 8877)

        # setting a bad parameter fails
        with self.assertRaises(KeyError):
            self.params.somewrongthing = 5

    def test_params_load(self):
        jsbuf = StringIO.StringIO('{"fridge_setpoint": 999}')

        self.params.load(f=jsbuf)
        self.assertEqual(self.params.fridge_setpoint, 999)

        with self.assertRaises(params.Params.Error):
            jsbuf = StringIO.StringIO('{"something_else": 999}')
            self.params.load(f=jsbuf)

        with self.assertRaises(KeyError):
            x = self.params.something_else

    def test_params_save(self):
        jsbuf = StringIO.StringIO()

        self.params.overshoot_delay = 123
        self.params.save(f=jsbuf)

        s = jsbuf.getvalue()
        self.assertTrue('"overshoot_delay": 123' in s, msg=s)
            
unittest.main()
