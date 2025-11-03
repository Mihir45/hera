#!/usr/bin/env python

"""Echo server using the asyncio API."""

from http import HTTPStatus
import asyncio
import json
import time

from websockets import ServerConnection
from websockets.asyncio.server import serve

import config
from controller import Controller
from db import cur, con

ws_conns: set[ServerConnection] = set()


async def pub(frame, orientation):
    cur.execute(
        """
        INSERT INTO frames (
            date, temperature, humidity, lux, infrared, visible,
            acceleration_x, acceleration_y, acceleration_z,
            gyro_x, gyro_y, gyro_z,
            magnetic_x, magnetic_y, magnetic_z
        )
        VALUES (
            CURRENT_TIMESTAMP, ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?
        );
    """,
        (
            frame.temperature,
            frame.humidity,  # fixed to match DB column name
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
        ),
    )
    con.commit()

    data = json.dumps(
        {
            "frame": frame.dict(),
            "orientation": orientation.dict(),
        }
    )

    # Send to all websocket clients
    for ws in set(ws_conns):
        try:
            await ws.send(data)
        except Exception:
            ws_conns.discard(ws)


async def collect():
    print("starting collector")
    controller = Controller(config.FAKE_DATA)
    while True:
        start_time = time.monotonic()

        frame = controller.read()
        orientation = controller.compute_orientation(frame)
        await pub(frame, orientation)
        await asyncio.sleep(config.DELTA_TIME - time.monotonic() + start_time)


async def ws_handle(ws: ServerConnection):
    print("received websocket connection")
    ws_conns.add(ws)
    try:
        await ws.wait_closed()
    finally:
        ws_conns.remove(ws)


from urllib.parse import parse_qs


async def http_handle(conn, req):
    if req.path == "/index":
        resp = conn.respond(HTTPStatus.OK, open("index.html").read())
        resp.headers["content-type"] = "text/html"
        return resp
    if req.path.startswith("/query"):
        qs = parse_qs(req.path[7:])
        start = qs.get("start")
        end = qs.get("end")

        frames = cur.execute(
            """
WITH params AS (
    SELECT 
        :start_ts::timestamp AS start_ts,
        :end_ts::timestamp AS end_ts,
        :num_samples AS num_samples  -- e.g., 1000
),
buckets AS (
    SELECT 
        time_bucket((end_ts - start_ts) / num_samples, ts) AS bucket_ts
    FROM frames, params
    WHERE ts BETWEEN start_ts AND end_ts
    GROUP BY bucket_ts  -- This ensures buckets are created dynamically
)
SELECT 
    b.bucket_ts,
    AVG(f.temperature) AS avg_temperature,
    AVG(f.humidity) AS avg_humidity,
    AVG(f.lux)::INTEGER AS avg_lux,  -- Cast back to int if needed
    AVG(f.infrared)::INTEGER AS avg_infrared,
    AVG(f.visible)::INTEGER AS avg_visible,
    AVG(f.acceleration_x) AS avg_acceleration_x,
    AVG(f.acceleration_y) AS avg_acceleration_y,
    AVG(f.acceleration_z) AS avg_acceleration_z,
    AVG(f.gyro_x) AS avg_gyro_x,
    AVG(f.gyro_y) AS avg_gyro_y,
    AVG(f.gyro_z) AS avg_gyro_z,
    AVG(f.magnetic_x) AS avg_magnetic_x,
    AVG(f.magnetic_y) AS avg_magnetic_y,
    AVG(f.magnetic_z) AS avg_magnetic_z
FROM buckets b
LEFT JOIN frames f ON f.ts >= b.bucket_ts AND f.ts < b.bucket_ts + ((SELECT end_ts - start_ts FROM params) / (SELECT num_samples FROM params))
WHERE f.ts BETWEEN (SELECT start_ts FROM params) AND (SELECT end_ts FROM params)
GROUP BY b.bucket_ts
ORDER BY b.bucket_ts;""",
            (start, end, 100),
        ).fetchall()

        print(len(frames))

        return conn.respond(HTTPStatus.OK, json.dumps(frames))

    if req.path != "/ws":
        return conn.respond(HTTPStatus.NOT_FOUND, "Not Found")


async def ws_start():
    if not config.WEBSOCKET_ENABLED:
        return

    print("starting websocket server")
    async with serve(
        ws_handle, "0.0.0.0", config.WEBSOCKET_PORT, process_request=http_handle
    ) as server:
        await server.serve_forever()


async def main():
    await asyncio.gather(collect(), ws_start())


if __name__ == "__main__":
    asyncio.run(main())
