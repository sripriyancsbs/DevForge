# {{APPLICATION_NAME}}

{{DESCRIPTION}}

FastAPI application scaffolded via the DevForge platform template.

## Features
- **Runtime**: Python 3.12 (FastAPI)
- **Port**: {{PORT}}
- **Environment**: {{ENVIRONMENT}}
- **Health check**: `GET /healthz`
- **Documentation**: Automatic OpenAPI Swagger UI at `GET /docs`

## Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run test suite
pytest

# Start local server
uvicorn main:app --host 0.0.0.0 --port {{PORT}} --reload
```

## Docker Container
```bash
docker build -t {{APPLICATION_NAME}}:latest .
docker run -p {{PORT}}:{{PORT}} {{APPLICATION_NAME}}:latest
```
