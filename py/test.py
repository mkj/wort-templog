import unittest
import sensor_ds18b20

class TestSensors(unittest.TestCase):
    def setUp(self):
        self.sensors = sensor_ds18b20.DS18B20s(None)

    def test_re(self):
        f1 = """6e 01 4b 46 7f ff 02 10 71 : crc=71 YES
6e 01 4b 46 7f ff 02 10 71 t=22875
"""
        val = self.sensors.do_sensor_name('blank', f1)
        self.assertEqual(val, 22.875)

        f2 = """6e 01 4b 46 7f ff 02 10 71 : crc=71 NO
6e 01 4b 46 7f ff 02 10 71 t=22875
"""
        val = self.sensors.do_sensor_name('blank', f2)
        self.assertEqual(val, None)

        f3 = """6e 01 4b 46 7f ff 02 10 71 : crc=71 YES
6e 01 4b 46 7f ff 02 10 71 t=-1
"""
        val = self.sensors.do_sensor_name('blank', f3)
        self.assertEqual(val, -0.001)

unittest.main()
