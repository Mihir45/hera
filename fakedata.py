from db import cur, con
from datetime import datetime, timedelta
from controller import Controller

ctr = Controller(True)
start = datetime(datetime.now().year, 6, 1)
end = datetime.now()
step = timedelta(seconds=1)

BATCH_SIZE = 10000  # adjust for memory vs speed
batch = []

while start <= end:
    frame = ctr.fake()
    batch.append((
        start,
        frame.temperature,
        frame.humidity,
        frame.lux,
        frame.infrared,
        frame.visible,
        frame.acceleration[0],
        frame.acceleration[1],
        frame.acceleration[2],
        frame.gyro[0],
        frame.gyro[1],
        frame.gyro[2],
        frame.magnetic[0],
        frame.magnetic[1],
        frame.magnetic[2],
    ))

    if len(batch) >= BATCH_SIZE:
        cur.executemany("""
            INSERT INTO frames (
                date, temperature, humidity, lux, infrared, visible,
                acceleration_x, acceleration_y, acceleration_z,
                gyro_x, gyro_y, gyro_z,
                magnetic_x, magnetic_y, magnetic_z
            )
            VALUES (?, ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?)
        """, batch)
        con.commit()
        batch.clear()

    start += step

# Insert any remaining rows
if batch:
    cur.executemany("""
        INSERT INTO frames (
            date, temperature, humidity, lux, infrared, visible,
            acceleration_x, acceleration_y, acceleration_z,
            gyro_x, gyro_y, gyro_z,
            magnetic_x, magnetic_y, magnetic_z
        )
        VALUES (?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?)
    """, batch)
    con.commit()

con.close()
