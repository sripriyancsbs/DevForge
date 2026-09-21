# {{APPLICATION_NAME}}

{{DESCRIPTION}}

Go Gin API microservice scaffolded via the DevForge platform template.

## Features
- **Runtime**: Go 1.22
- **Framework**: Gin Gonic
- **Port**: {{PORT}}
- **Environment**: {{ENVIRONMENT}}
- **Health check**: `GET /healthz`

## Local Development
```bash
# Download dependencies
go mod download

# Run test suite
go test -v ./...

# Start server
go run .
```

## Docker Container
```bash
docker build -t {{APPLICATION_NAME}}:latest .
docker run -p {{PORT}}:{{PORT}} {{APPLICATION_NAME}}:latest
```
