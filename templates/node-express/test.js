const assert = require('assert');
const http = require('http');
const app = require('./server');

const testPort = 3999;
const server = app.listen(testPort, () => {
  console.log(`Running test suite on port ${testPort}...`);

  // Test 1: GET /healthz
  http.get(`http://localhost:${testPort}/healthz`, (res) => {
    assert.strictEqual(res.statusCode, 200, 'Health check should return 200 OK');
    let raw = '';
    res.on('data', chunk => raw += chunk);
    res.on('end', () => {
      const body = JSON.parse(raw);
      assert.strictEqual(body.status, 'healthy', 'Status should be healthy');
      console.log('  ✓ GET /healthz returned 200 healthy');

      // Test 2: GET /
      http.get(`http://localhost:${testPort}/`, (resRoot) => {
        assert.strictEqual(resRoot.statusCode, 200, 'Root should return 200 OK');
        console.log('  ✓ GET / returned 200 OK');
        server.close(() => {
          console.log('All tests passed successfully!');
          process.exit(0);
        });
      });
    });
  }).on('error', (err) => {
    console.error('Test failed with network error:', err);
    server.close(() => process.exit(1));
  });
});
