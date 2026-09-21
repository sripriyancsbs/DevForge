const express = require('express');

const app = express();
const PORT = process.env.PORT || {{PORT}};

app.use(express.json());

// Health check probe
app.get('/healthz', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    service: '{{APPLICATION_NAME}}',
    environment: '{{ENVIRONMENT}}',
    timestamp: new Date().toISOString()
  });
});

// Root endpoint
app.get('/', (req, res) => {
  res.status(200).json({
    message: 'Node.js Express service {{APPLICATION_NAME}} running on DevForge IDP',
    version: '{{VERSION}}'
  });
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`[DevForge] {{APPLICATION_NAME}} Express server listening on port ${PORT}`);
  });
}

module.exports = app;
