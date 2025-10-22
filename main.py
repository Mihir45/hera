#!/usr/bin/env python

"""Echo server using the asyncio API."""

from http import HTTPStatus
import asyncio
import json

from websockets import ServerConnection
from websockets.asyncio.server import serve

import config
from controller import Controller
from db import cur, con

ws_conns: set[ServerConnection] = set()


async def pub(frame, orientation):
    cur.execute("""
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
    """, (
        frame.temperature,
        frame.humidity,       # fixed to match DB column name
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
        frame = controller.read()
        orientation = controller.compute_orientation(frame)
        await pub(frame, orientation)
        await asyncio.sleep(0.5)


async def ws_handle(ws: ServerConnection):
    print("received websocket connection")
    ws_conns.add(ws)
    try:
        await ws.wait_closed()
    finally:
        ws_conns.remove(ws)

from urllib.parse import parse_qs

async def http_handle(conn, req):
    if req.path=="/index":
        resp = conn.respond(HTTPStatus.OK, open("index.html").read())
        resp.headers["content-type"] = "text/html"
        return resp
    if req.path.startswith("/query"):
        qs = parse_qs(req.path[7:])
        start = qs.get("start")
        end = qs.get("end")
        print(start, end)
        start_id,  = cur.execute("SELECT id FROM frames WHERE date >= ? ORDER BY id ASC LIMIT 1", (start)).fetchone()
        end_id,  = cur.execute("SELECT id FROM frames WHERE date <= ? ORDER BY id DESC LIMIT 1",(end)).fetchone()
        print(start_id, end_id)
        delta = (end_id - start_id) // 1000
        print(delta)
        frames = cur.execute("SELECT * FROM frames WHERE id % ? = 0 AND id >= ? AND id <= ? ORDER BY id ASC", (delta, start_id, end_id)).fetchall()
        print(len(frames))
        return conn.respond(HTTPStatus.OK, json.dumps(frames))

    if req.path != "/ws":
        return conn.respond(HTTPStatus.NOT_FOUND, "Not Found")


async def ws_start():
    if not config.WEBSOCKET_ENABLED:
        return

    print("starting websocket server")
    async with serve(ws_handle, "0.0.0.0", config.WEBSOCKET_PORT, process_request=http_handle) as server:
        await server.serve_forever()

async def main():
    await asyncio.gather(collect(), ws_start())

if __name__ == "__main__":
    asyncio.run(main())