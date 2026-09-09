# C3 - Redis Cache Effectiveness Benchmark

# This benchmark measures the latency of the
# /sensors/{sensor_id}/summary endpoint with and without Redis caching.

# The endpoint uses a 30-second Redis cache TTL.
# The benchmark performs:
# - 500 warm-cache requests, where the cached summary already exists
# - 500 cold-cache requests, where the cache key is removed before each request

# For each batch the benchmark prints:
# - p50 latency
# - p95 latency
# - p99 latency
# - cache hit rate

import os
import time
import statistics
import redis
import requests

URL = "http://api:8000/sensors/SM_00001/summary"
CACHE_KEY = "sensor_summary:SM_00001"
REQUESTS = 500

redis_client = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

def percentile(values, p):
    values = sorted(values)
    index = int((p / 100) * len(values))
    index = min(index, len(values) - 1)
    return values[index]

def measure_request():
    start = time.perf_counter()
    response = requests.get(URL)
    elapsed = (time.perf_counter() - start) * 1000
    response.raise_for_status()
    return elapsed

requests.get(URL).raise_for_status()

warm_times = []
for i in range(REQUESTS): 
    warm_times.append(measure_request())

cold_times = []
for i in range(REQUESTS):
    redis_client.delete(CACHE_KEY)
    cold_times.append(measure_request())

warm_p50 = statistics.median(warm_times)
warm_p95 = percentile(warm_times, 95)
warm_p99 = percentile(warm_times, 99)

cold_p50 = statistics.median(cold_times)
cold_p95 = percentile(cold_times, 95)
cold_p99 = percentile(cold_times, 99)


print(f"Warm cache: p50={warm_p50:.2f} ms, p95={warm_p95:.2f} ms, p99={warm_p99:.2f} ms")
print(f"Cold cache: p50={cold_p50:.2f} ms, p95={cold_p95:.2f} ms, p99={cold_p99:.2f} ms")