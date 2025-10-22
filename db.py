import sqlite3

con=sqlite3.connect("fake.db")

cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS frames (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATETIME NOT NULL,
    temperature FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    lux INT NOT NULL,
    infrared INT NOT NULL,
    visible INT NOT NULL,
    acceleration_x FLOAT NOT NULL,
    acceleration_y FLOAT NOT NULL,
    acceleration_z FLOAT NOT NULL,
    gyro_x FLOAT NOT NULL,
    gyro_y FLOAT NOT NULL,
    gyro_z FLOAT NOT NULL,
    magnetic_x FLOAT NOT NULL,
    magnetic_y FLOAT NOT NULL,
    magnetic_z FLOAT NOT NULL
);
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_frames_date ON frames (date);
""")
