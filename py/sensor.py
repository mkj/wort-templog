import os

def make_sensor(server):
    if server.test_mode():
        import sensor_test
        return sensor_test.SensorTest(server)
    else:
        import sensor_ds18b20
        return sensor_ds18b20.SensorDS18B20(server)

