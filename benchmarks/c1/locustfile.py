# C1 - Cassandra Write Throughput Benchmark

# This benchmark measures the sustained write performance of the
# sensor_readings table using three Cassandra consistency levels:
# ONE, LOCAL_QUORUM and ALL.

# Locust generates a fixed workload of 30 concurrent users for
# 30 seconds. Each user continuously inserts sensor readings into
# Cassandra. The consistency level is selected using the
# C1_CONSISTENCY environment variable.

# Locust measures and prints:
# - total number of writes
# - writes per second
# - p50 write latency
# - p95 write latency
# - number of failed writes

# Each consistency level is tested manually three times using the
# same workload so that the results can be compared fairly.

import os
import time
from datetime import datetime, timezone

from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster
from locust import User, task, LoadTestShape


CONSISTENCY_LEVELS = {
    "ONE": ConsistencyLevel.ONE,
    "LOCAL_QUORUM": ConsistencyLevel.LOCAL_QUORUM,
    "ALL": ConsistencyLevel.ALL
}

CONSISTENCY = os.getenv("C1_CONSISTENCY", "ONE")

cluster = Cluster(["timeseries-db"], protocol_version=5)
session = cluster.connect()

statement = session.prepare("""
    INSERT INTO gridsense.sensor_readings
    (sensor_id, reading_time, metric_type, value, unit, quality_flag)
    VALUES (?, ?, ?, ?, ?, ?)
""")

statement.consistency_level = CONSISTENCY_LEVELS[CONSISTENCY]


class CassandraUser(User):

    def on_start(self):
        self.sensor_id = f"BENCH_{id(self)}"

    @task
    def write_reading(self):
        start = time.perf_counter()

        try:
            session.execute(statement, (
                self.sensor_id,
                datetime.now(timezone.utc),
                "voltage",
                230.0,
                "V",
                0
            ))

            response_time = (time.perf_counter() - start) * 1000

            self.environment.events.request.fire(
                request_type="Cassandra",
                name=f"INSERT {CONSISTENCY}",
                response_time=response_time,
                response_length=0,
                exception=None
            )

        except Exception as error:
            response_time = (time.perf_counter() - start) * 1000

            self.environment.events.request.fire(
                request_type="Cassandra",
                name=f"INSERT {CONSISTENCY}",
                response_time=response_time,
                response_length=0,
                exception=error
            )


class BenchmarkShape(LoadTestShape):

    def tick(self):
        # 30 concurrent users, spawn rate 30 users/s, duration 30 seconds.
        if self.get_run_time() < 30:
            return 30, 30

        return None