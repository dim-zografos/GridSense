import asyncio
import os

from cassandra.cluster import Cluster


cluster = None
session = None


async def connect():
    global cluster, session

    host = os.getenv("CASSANDRA_HOST")
    port = os.getenv("CASSANDRA_PORT")
    keyspace = os.getenv("CASSANDRA_KEYSPACE")

    if not host or not port or not keyspace:
        raise RuntimeError("Cassandra environment variables are not configured")

    cluster = Cluster([host], port=int(port))
    session = await asyncio.to_thread(cluster.connect, keyspace)


def get_session():
    if session is None:
        raise RuntimeError("Cassandra session is not initialized")

    return session


async def close():
    global cluster, session

    if cluster is not None:
        await asyncio.to_thread(cluster.shutdown)

    session = None
    cluster = None