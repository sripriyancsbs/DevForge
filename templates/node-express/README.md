# {{APPLICATION_NAME}}

{{DESCRIPTION}}

Node.js Express API scaffolded via the DevForge platform template.

## Features
- **Runtime**: Node.js 20
- **Framework**: Express
- **Port**: {{PORT}}
- **Environment**: {{ENVIRONMENT}}
- **Health check**: `GET /healthz`

## Local Development
```bash
# Install dependencies
npm install

# Run test suite
npm test

# Start local server
npm start
```

## Docker Container
```bash
docker build -t {{APPLICATION_NAME}}:latest .
docker run -p {{PORT}}:{{PORT}} {{APPLICATION_NAME}}:latest
```
