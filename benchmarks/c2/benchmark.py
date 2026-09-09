# C2 - Neo4j Graph Traversal Depth Benchmark

# This benchmark measures the latency of the fault-impact endpoint
# as the maximum Neo4j traversal depth increases from 1 to 8.

# The same seeded node (GSP_NORTH) is used for every test because it
# has more than 20 downstream nodes. For each depth, the endpoint is
# called 30 times using the same conditions.

# The benchmark measures and prints:
# - median (p50) response latency
# - p95 response latency

# The results are used to examine how graph traversal depth affects
# latency and whether the 200 ms SLA is exceeded.

import time
import statistics

import requests


URL = "http://api:8000/grid/fault-impact/GSP_NORTH"
ITERATIONS = 30


def percentile(values, percentile):
    values = sorted(values)
    index = int((percentile / 100) * len(values))
    index = min(index, len(values) - 1)
    return values[index]


for depth in range(1, 9):
    times = []

    for i in range(ITERATIONS):
        start = time.perf_counter()

        response = requests.get(
            URL,
            params={"max_depth": depth}
        )

        elapsed = (time.perf_counter() - start) * 1000

        response.raise_for_status()
        times.append(elapsed)

    median = statistics.median(times)
    p95 = percentile(times, 95)

    print(f"Depth {depth}: median={median:.2f} ms, p95={p95:.2f} ms")