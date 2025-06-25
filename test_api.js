// Test script to verify Agent-MCP API is accessible
const http = require('http');

const options = {
  hostname: 'localhost',
  port: 8080,
  path: '/api/status',
  method: 'GET',
  headers: {
    'Content-Type': 'application/json',
    'Origin': 'http://localhost:3000'
  }
};

console.log('Testing Agent-MCP API at http://localhost:8080/api/status');

const req = http.request(options, (res) => {
  console.log(`Status Code: ${res.statusCode}`);
  console.log('Headers:', res.headers);
  
  let data = '';
  
  res.on('data', (chunk) => {
    data += chunk;
  });
  
  res.on('end', () => {
    try {
      const json = JSON.parse(data);
      console.log('Response:', JSON.stringify(json, null, 2));
      
      if (res.headers['access-control-allow-origin']) {
        console.log('\n✓ CORS headers are present!');
        console.log('Access-Control-Allow-Origin:', res.headers['access-control-allow-origin']);
      } else {
        console.log('\n✗ CORS headers are missing!');
      }
    } catch (e) {
      console.log('Raw response:', data);
    }
  });
});

req.on('error', (error) => {
  console.error('Error:', error.message);
});

req.end();