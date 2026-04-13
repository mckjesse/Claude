import { useEffect } from 'react';

// Single shared EventSource — all hooks share one SSE connection
let eventSource = null;
let listeners = new Map(); // event -> Set<callback>

function ensureConnection() {
  if (eventSource) return;
  eventSource = new EventSource('/api/events');
  eventSource.onerror = () => {
    // Reconnect after 3s on error
    eventSource?.close();
    eventSource = null;
    setTimeout(ensureConnection, 3000);
  };
}

function subscribe(event, callback) {
  ensureConnection();
  if (!listeners.has(event)) {
    listeners.set(event, new Set());
    // Register the SSE listener for this event type
    eventSource.addEventListener(event, (e) => {
      const cbs = listeners.get(event);
      if (cbs) cbs.forEach((cb) => cb(JSON.parse(e.data)));
    });
  }
  listeners.get(event).add(callback);
}

function unsubscribe(event, callback) {
  const cbs = listeners.get(event);
  if (cbs) {
    cbs.delete(callback);
  }
}

/**
 * Subscribe to a realtime event from the server.
 * `event` matches the event name broadcast by the server (e.g. 'tools', 'movements').
 */
export function useRealtime(event, callback) {
  useEffect(() => {
    subscribe(event, callback);
    return () => unsubscribe(event, callback);
  }, [event, callback]);
}
