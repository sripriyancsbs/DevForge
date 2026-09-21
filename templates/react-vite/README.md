# {{APPLICATION_NAME}}

{{DESCRIPTION}}

React + Vite frontend application scaffolded via the DevForge platform template.

## Features
- **Runtime**: Node.js 20 (Vite)
- **Port**: {{PORT}}
- **Environment**: {{ENVIRONMENT}}

## Local Development
```bash
npm install
npm run dev
```

## Docker Container
```bash
docker build -t {{APPLICATION_NAME}}:latest .
docker run -p {{PORT}}:80 {{APPLICATION_NAME}}:latest
```
