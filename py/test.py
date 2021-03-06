import io

import unittest
import sensor_ds18b20
import params

class TestSensors(unittest.TestCase):
    def setUp(self):
        self.sensors = sensor_ds18b20.SensorDS18B20(None)

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
        jsbuf = io.StringIO('{"fridge_setpoint": 999}')

        self.params.load(f=jsbuf)
        self.assertEqual(self.params.fridge_setpoint, 999)

        with self.assertRaises(params.Params.Error):
            jsbuf = io.StringIO('{"something_else": 999}')
            self.params.load(f=jsbuf)

        with self.assertRaises(KeyError):
            x = self.params.something_else

    def test_params_save(self):
        jsbuf = io.StringIO()

        self.params.overshoot_delay = 123
        s = self.params.save_string()
        self.assertTrue('"overshoot_delay": 123' in s, msg=s)
            
unittest.main()
