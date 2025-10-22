import board
import busio
import time
import json
import numpy as np
import adafruit_lsm9ds1

# I2C setup
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_lsm9ds1.LSM9DS1_I2C(i2c)

# Storage
accel_data = []
gyro_data = []
mag_data = []

print("📊 Collecting data for 30 seconds... Move the sensor in all orientations.")

start_time = time.time()
while time.time() - start_time < 30:
    accel_data.append(tuple(sensor.acceleration))
    gyro_data.append(tuple(sensor.gyro))
    mag_data.append(tuple(sensor.magnetic))
    time.sleep(0.05)  # 20Hz

# Convert to numpy arrays
accel_data = np.array(accel_data)
gyro_data = np.array(gyro_data)
mag_data = np.array(mag_data)

# ---------------------------
# Calibrate Gyroscope (bias)
gyro_bias = np.mean(gyro_data, axis=0)

# Calibrate Accelerometer (offset and scale)
accel_offset = (np.max(accel_data, axis=0) + np.min(accel_data, axis=0)) / 2
accel_scale = (np.max(accel_data, axis=0) - np.min(accel_data, axis=0)) / 2
avg_accel_scale = np.mean(accel_scale)
accel_scale_factors = avg_accel_scale / accel_scale

# Calibrate Magnetometer (offset and scale)
mag_offset = (np.max(mag_data, axis=0) + np.min(mag_data, axis=0)) / 2
mag_scale = (np.max(mag_data, axis=0) - np.min(mag_data, axis=0)) / 2
avg_mag_scale = np.mean(mag_scale)
mag_scale_factors = avg_mag_scale / mag_scale

# Save to JSON
calibration = {
    "gyro_bias": gyro_bias.tolist(),
    "accel_offset": accel_offset.tolist(),
    "accel_scale": accel_scale_factors.tolist(),
    "mag_offset": mag_offset.tolist(),
    "mag_scale": mag_scale_factors.tolist()
}

with open("lsm9ds1_calibration.json", "w") as f:
    json.dump(calibration, f, indent=4)

print("✅ Calibration complete and saved to lsm9ds1_calibration.json")
