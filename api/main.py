from fastapi import FastAPI

app = FastAPI(
    title="GridSense API",
    description="REST API gateway for the GridSense prototype",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}