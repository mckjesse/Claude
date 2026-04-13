// Simple SSE broadcaster — keeps track of connected clients
// and pushes events when data changes.

const clients = new Set();

export function sseHandler(req, res) {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  });

  // Send initial connected event
  res.write('data: connected\n\n');

  clients.add(res);
  req.on('close', () => clients.delete(res));
}

export function broadcast(event, data) {
  const message = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
  for (const client of clients) {
    client.write(message);
  }
}
