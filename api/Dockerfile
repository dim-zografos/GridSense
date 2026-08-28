# Python 3.11 image as the base image for the API service.
FROM python:3.11-slim


WORKDIR /app

# Python dependencies required by the FastAPI application.
# --no-cache-dir keeps the image smaller by avoiding pip cache files.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# API source code into the container.
COPY . .

# FastAPI application using Uvicorn.
# app object from main.py.
# 0.0.0.0 allows the app to be reachable from outside the container.
# Port 8000 is exposed through docker-compose.yml.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]