#!/usr/bin/env bash
set -e

mkdir -p /tmp/inventory-app
cd /tmp/inventory-app

cat > main.py << 'PYEOF'
from fastapi import FastAPI

app = FastAPI(title="inventory-api", version="1.0.0")

@app.get("/healthz")
def health_check():
    return {"status": "ok", "service": "inventory-api"}

@app.get("/")
def root():
    return {"message": "Service inventory-api is running on DevForge Kubernetes"}
PYEOF

cat > requirements.txt << 'REQEOF'
fastapi>=0.110.0
uvicorn>=0.28.0
REQEOF

cat > Dockerfile << 'DOCEOF'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
DOCEOF

echo "Building Docker image ghcr.io/sripriyancsbs/inventory-api:sha-abc1234..."
docker build -t ghcr.io/sripriyancsbs/inventory-api:sha-abc1234 .

echo "Loading image into kind devforge cluster..."
kind load docker-image ghcr.io/sripriyancsbs/inventory-api:sha-abc1234 --name devforge
echo "Successfully built and loaded image into kind cluster!"
