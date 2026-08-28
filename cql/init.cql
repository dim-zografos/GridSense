-- cql/init.cql (starter — you must complete and extend this)

CREATE KEYSPACE IF NOT EXISTS gridsense
WITH replication = {
'class': 'SimpleStrategy',
'replication_factor': 1 -- use 3 in production; 1 is fine for dev
};

USE gridsense;

-- Table 1: Optimised for query pattern (1) — readings per sensor over time

CREATE TABLE IF NOT EXISTS sensor_readings (
sensor_id TEXT,
reading_time TIMESTAMP,
metric_type TEXT, -- 'voltage', 'current', 'power_factor', 'temp'
value FLOAT,
unit TEXT,
quality_flag TINYINT, -- 0=good, 1=suspect, 2=bad
PRIMARY KEY ((sensor_id), reading_time)
) WITH CLUSTERING ORDER BY (reading_time DESC)
AND default_time_to_live = 7776000; -- 90 days

-- Table 2: relay operation log — append-only, causal order preserved

CREATE TABLE IF NOT EXISTS relay_events (
feeder_id TEXT,
event_time TIMEUUID, -- TIMEUUID embeds causal timestamp
relay_id TEXT,
event_type TEXT, -- 'TRIP', 'RECLOSE', 'LOCKOUT'
fault_type TEXT,
current_kA FLOAT,
PRIMARY KEY ((feeder_id), event_time)
) WITH CLUSTERING ORDER BY (event_time ASC);

-- Table 3: Optimised for query pattern (2) — cross-network readings for live dashboard

CREATE TABLE IF NOT EXISTS sensor_readings_by_bucket (
    bucket_start TIMESTAMP,
    shard INT,
    reading_time TIMESTAMP,
    sensor_id TEXT,
    metric_type TEXT,
    value FLOAT,
    unit TEXT,
    quality_flag TINYINT,
    PRIMARY KEY ((bucket_start, shard), reading_time, sensor_id, metric_type)
) WITH CLUSTERING ORDER BY (reading_time DESC)
AND default_time_to_live = 7776000;