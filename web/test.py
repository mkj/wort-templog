#!/usr/bin/env python
import log
import time

log.sensor_update("test1", [22,22,22.1,22.4,22.5], time.time() - 10, 300)
