import config

import time
import math
import random
import json

import board
import busio

import adafruit_tsl2591
import adafruit_lsm9ds1
#import adafruit_am2320
import adafruit_dht

import numpy as np
from ahrs.common.orientation import q2euler
from ahrs.filters import Madgwick

from frame import Frame
from orientation import Orientation


class Controller:
    fuse = Madgwick(Dt=config.DELTA_TIME)
    q = np.array([1.0, 0.0, 0.0, 0.0])  # initial quaternion
    last_time = time.monotonic()

    def __init__(self, fake: bool):
        if fake:
            self.prev = None
            return

        self.i2c = board.I2C()

        try:
            self.tsl = adafruit_tsl2591.TSL2591(self.i2c)
        except Exception as e:
            self.tsl = None
            print(e)
            print("ERROR: Failed to initialize TSL2591 Light Sensor")

        try:
            self.lsm = adafruit_lsm9ds1.LSM9DS1_I2C(self.i2c)
            # self.lsm.accel_range = adafruit_lsm9ds1.ACCELRANGE_16G
            # self.lsm.mag_gain = adafruit_lsm9ds1.MAGGAIN_16GAUSS
            # self.lsm.gyro_scale = adafruit_lsm9ds1.GYROSCALE_2000DPS

        except:
            self.lsm = None
            print(e)
            print("ERROR: Failed to initialize LSM9DS1 Accel/Mag/Gyro Sensor")
        
        try:
            self.dht = adafruit_dht.DHT11(board.D17)
        except Exception as e:
            self.dht = None
            print(e)
            print("Error: Failed to initialize DHT Temperature & Relative Humidity Sensor")
        
        with open("lsm9ds1_calibration.json") as f:
            self.cal = json.load(f)

    def compute_orientation(self, frame: Frame) -> Orientation:
        accel = np.array(frame.acceleration)
        
        gyro = np.array(frame.gyro)
        
        mag = np.array(frame.magnetic)
        

        self.q = self.fuse.updateMARG(q=self.q, acc=accel, gyr=gyro, mag=mag)

        roll, pitch, yaw = np.degrees(q2euler(self.q))
        o = Orientation()
        o.roll = roll
        o.pitch = pitch
        o.yaw = yaw

        return o

    def calibrate_gyro(self, raw):
        return np.array(raw) - np.array(self.cal["gyro_bias"])

    def calibrate_accel(self, raw):
        return (np.array(raw) - np.array(self.cal["accel_offset"])) * np.array(self.cal["accel_scale"])

    def calibrate_mag(self, raw):
        return (np.array(raw) - np.array(self.cal["mag_offset"])) * np.array(self.cal["mag_scale"])

    def read(self) -> Frame:
        if config.FAKE_DATA:
            return self.fake()

        cur_time = time.monotonic()
        f = Frame()
        
        # print(cur_time - self.last_time) DELTA_TIME

        self.last_time = cur_time

        # Read temperature and humidity from AM2320
        try:
            if self.dht is not None:
                f.temperature = float(self.dht.temperature)
                f.humidity = float(self.dht.humidity)
            else:
                f.temperature = 0
                f.humidity = 0
        except Exception as e:
            print("DHT", e)
            f.temperature = 0
            f.humidity = 0

        # Read light data from TSL2591
        try:
            if self.tsl is not None:
                f.lux = int(self.tsl.lux)
                f.infrared = int(self.tsl.infrared)
                f.visible = int(self.tsl.visible)
            else:
                f.lux = 0
                f.infrared = 0
                f.visible = 0
        except Exception as e:
            print("TSL", e)
            f.lux = 0
            f.infrared = 0
            f.visible = 0


        # Read motion data from LSM9DS1
        try:
            if self.lsm is not None:
                accel = self.lsm.acceleration
                gyro = self.lsm.gyro
                mag = self.lsm.magnetic
                
                f.acceleration = tuple(map(float, accel))
                # f.acceleration = (-f.acceleration[1], -f.acceleration[0], f.acceleration[2])

                f.gyro = tuple(map(float, gyro)) #convert ut to gauss

                # gyro = (-f.gyro[1], -f.gyro[0], f.gyro[2])
                f.magnetic = tuple(map(lambda x: float(x) * 0.01, mag))

                # f.acceleration = self.calibrate_accel(tuple(float(x) for x in accel)).tolist()
                # f.gyro = self.calibrate_gyro(tuple(float(x) for x in gyro)).tolist()
                # f.magnetic = self.calibrate_mag(tuple(float(x) for x in mag)).tolist()
            else:
                f.acceleration = (0, 0, 0)
                f.gyro = (0, 0, 0)
                f.magnetic = (0, 0, 0)
                
        except Exception as e:
            print("LSM", e)
            f.acceleration = (0, 0, 0)
            f.gyro = (0, 0, 0)
            f.magnetic = (0, 0, 0)

        self.prev = f
        return f

    def fake(self) -> Frame:
        t = time.time()
        f = Frame()

        # Temperature: daily cycle + noise + slow drift
        base_temp = 22 + 5 * math.sin(2 * math.pi * (t % 86400) / 86400)
        temp_noise = random.gauss(0, 0.1)
        if self.prev:
            f.temperature = round(self.prev.temperature + random.gauss(0, 0.02), 2)
        else:
            f.temperature = round(base_temp + temp_noise, 2)

        # Humidity: inverse to temperature + noise
        base_hum = 60 - 10 * math.sin(2 * math.pi * (t % 86400) / 86400)
        hum_noise = random.gauss(0, 0.2)
        if self.prev:
            f.humidity = round(self.prev.humidity + random.gauss(0, 0.05), 2)
        else:
            f.humidity = round(base_hum + hum_noise, 2)

        # Lux: simulate day/night cycle
        day_frac = (t % 86400) / 86400
        if 0.23 < day_frac < 0.77:
            lux = 10000 + 40000 * math.sin(math.pi * (day_frac - 0.23) / 0.54)
        else:
            lux = 0
        f.lux = int(lux + random.gauss(0, 100))

        # Infrared/visible: proportional to lux + noise
        f.infrared = int(f.lux * 0.2 + random.gauss(0, 10))
        f.visible = int(f.lux * 0.8 + random.gauss(0, 20))

        # Acceleration: simulate small vibrations
        if self.prev:
            f.acceleration = tuple(
                round(a + random.gauss(0, 0.01), 3) for a in self.prev.acceleration
            )
        else:
            f.acceleration = (
                round(0.01 * math.sin(t), 3),
                round(0.01 * math.cos(t), 3),
                round(1 + 0.01 * math.sin(0.5 * t), 3),
            )

        # Gyro: simulate slow rotation
        if self.prev:
            f.gyro = tuple(round(g + random.gauss(0, 0.05), 3) for g in self.prev.gyro)
        else:
            f.gyro = (
                round(10 * math.sin(0.1 * t), 3),
                round(10 * math.cos(0.1 * t), 3),
                round(0.5 * math.sin(0.05 * t), 3),
            )

        # Magnetic: simulate Earth's field with noise
        if self.prev:
            f.magnetic = tuple(
                round(m + random.gauss(0, 0.2), 3) for m in self.prev.magnetic
            )
        else:
            f.magnetic = (
                round(30 + 2 * math.sin(0.01 * t), 3),
                round(-10 + 2 * math.cos(0.01 * t), 3),
                round(40 + 1 * math.sin(0.02 * t), 3),
            )

        self.prev = f
        return f
