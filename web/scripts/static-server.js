const fs = require('fs');
const http = require('http');
const path = require('path');

const webRoot = path.resolve(__dirname, '..');
const host = process.env.WEB_HOST || '127.0.0.1';
const port = Number(process.env.WEB_PORT || 4173);

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
};

function sendText(response, statusCode, message) {
  response.writeHead(statusCode, {
    'Content-Type': 'text/plain; charset=utf-8',
  });
  response.end(message);
}

const server = http.createServer((request, response) => {
  let pathname;

  try {
    pathname = decodeURIComponent(new URL(request.url, `http://${host}`).pathname);
  } catch {
    sendText(response, 400, 'Bad Request');
    return;
  }

  const requestedPath = pathname === '/' ? '/index.html' : pathname;
  const filePath = path.resolve(webRoot, `.${requestedPath}`);

  if (filePath !== webRoot && !filePath.startsWith(`${webRoot}${path.sep}`)) {
    sendText(response, 403, 'Forbidden');
    return;
  }

  fs.stat(filePath, (statError, stats) => {
    if (statError || !stats.isFile()) {
      sendText(response, 404, 'Not Found');
      return;
    }

    response.writeHead(200, {
      'Cache-Control': 'no-store',
      'Content-Type': contentTypes[path.extname(filePath)] || 'application/octet-stream',
    });

    const stream = fs.createReadStream(filePath);
    stream.on('error', () => {
      if (!response.headersSent) {
        sendText(response, 500, 'Internal Server Error');
      } else {
        response.destroy();
      }
    });
    stream.pipe(response);
  });
});

server.listen(port, host, () => {
  console.log(`Admin web running on http://${host}:${port}`);
});
