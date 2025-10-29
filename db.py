import psycopg2

conn = psycopg2.connect(
    "dbname=your_db user=your_user password=your_password host=your_host port=your_port"
)
cur = conn.cursor()

cur = con.cursor()

cur.execute(
    """
-- 1. Enable the extension (once per DB)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 2. Create the regular table (no AUTOINCREMENT – use GENERATED ALWAYS AS IDENTITY)
CREATE TABLE IF NOT EXISTS frames (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts            TIMESTAMP NOT NULL,
    temperature   DOUBLE PRECISION NOT NULL,
    humidity      DOUBLE PRECISION NOT NULL,
    lux           INTEGER NOT NULL,
    infrared      INTEGER NOT NULL,
    visible       INTEGER NOT NULL,
    acceleration_x DOUBLE PRECISION NOT NULL,
    acceleration_y DOUBLE PRECISION NOT NULL,
    acceleration_z DOUBLE PRECISION NOT NULL,
    gyro_x        DOUBLE PRECISION NOT NULL,
    gyro_y        DOUBLE PRECISION NOT NULL,
    gyro_z        DOUBLE PRECISION NOT NULL,
    magnetic_x    DOUBLE PRECISION NOT NULL,
    magnetic_y    DOUBLE PRECISION NOT NULL,
    magnetic_z    DOUBLE PRECISION NOT NULL
);

-- 3. Convert to a hypertable (partition by day – adjust chunk_time_interval as you like)
SELECT create_hypertable('frames', by_range('ts'), chunk_time_interval => INTERVAL '1 day');

-- 4. Index on the time column (automatically created by hypertable, but explicit is fine)
CREATE INDEX IF NOT EXISTS idx_frames_ts ON frames (ts DESC);

-- Enable compression (segments by 'ts' and compress other columns)
ALTER TABLE frames SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ts',
    timescaledb.compress_orderby = 'ts DESC'
);

-- Add a policy to automatically compress chunks older than 7 days
SELECT add_compression_policy('frames', INTERVAL '7 days');
"""
)
