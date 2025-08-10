const { createServer } = require('http');
const { parse } = require('url');
const next = require('next');

const dev = process.env.NODE_ENV !== 'production';
const app = next({ 
  dev,
  dir: __dirname,
  conf: {
    images: { unoptimized: true },
    eslint: { ignoreDuringBuilds: true },
    typescript: { ignoreBuildErrors: true }
  }
});
const handle = app.getRequestHandler();
const port = 3000;

app.prepare().then(() => {
  createServer((req, res) => {
    const parsedUrl = parse(req.url, true);
    handle(req, res, parsedUrl);
  }).listen(port, (err) => {
    if (err) throw err;
    console.log(`> Ready on http://localhost:${port}`);
  });
}).catch((err) => {
  console.error('Error starting server:', err);
  process.exit(1);
});