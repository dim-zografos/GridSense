from fastapi import FastAPI
from contextlib import asynccontextmanager
from db import neo4j, mongo, redis, postgres, cassandra
from routers import sensors, grid, equipment, billing, alerts

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # STARTUP
        await neo4j.connect()
        await mongo.connect()
        await redis.connect()
        await postgres.connect()
        await cassandra.connect()
        yield
    finally:
        # SHUTDOWN
        await neo4j.close()
        await mongo.close()
        await redis.close()
        await postgres.close()
        await cassandra.close()


app = FastAPI(
    title="GridSense API",
    description="REST API gateway for the GridSense prototype",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(sensors.router)
app.include_router(grid.router)
app.include_router(equipment.router)
app.include_router(billing.router)
app.include_router(alerts.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}