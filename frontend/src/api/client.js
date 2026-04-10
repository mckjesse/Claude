/**
 * API client that attaches the Entra access token to every request.
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

let _acquireToken = null;

/**
 * Called once at app startup to inject the MSAL token-acquisition function.
 */
export function setTokenAcquirer(fn) {
  _acquireToken = fn;
}

async function getHeaders() {
  const headers = { 'Content-Type': 'application/json' };

  if (_acquireToken) {
    try {
      const token = await _acquireToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    } catch {
      // Token acquisition failed — request will proceed unauthenticated
    }
  }

  return headers;
}

async function request(method, path, body) {
  const headers = await getHeaders();
  const opts = { method, headers };
  if (body !== undefined) {
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || JSON.stringify(error));
  }
  if (res.status === 204) return null;
  return res.json();
}

// ---- Tools ----
export const getTools = () => request('GET', '/tools/');
export const createTool = (data) => request('POST', '/tools/', data);
export const deleteTool = (id) => request('DELETE', `/tools/${id}/`);
export const allocateTool = (id, projectId) =>
  request('POST', `/tools/${id}/allocate/`, { project_id: projectId });
export const bulkImportTools = (tools) =>
  request('POST', '/tools/bulk-import/', { tools });

// ---- Projects ----
export const getProjects = () => request('GET', '/projects/');
export const createProject = (data) => request('POST', '/projects/', data);
export const deleteProject = (id) => request('DELETE', `/projects/${id}/`);

// ---- Dashboard ----
export const getDashboard = () => request('GET', '/dashboard/');

// ---- History ----
export const getHistory = () => request('GET', '/history/');

// ---- User ----
export const getMe = () => request('GET', '/me/');
