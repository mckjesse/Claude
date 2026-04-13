const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

export const api = {
  // Stats
  getStats: () => request('/stats'),

  // Tools
  getTools: (location) => request(`/tools${location ? `?location=${location}` : ''}`),
  createTool: (body) => request('/tools', { method: 'POST', body: JSON.stringify(body) }),
  assignTool: (id, body) => request(`/tools/${id}/assign`, { method: 'POST', body: JSON.stringify(body) }),
  returnTool: (id, body) => request(`/tools/${id}/return`, { method: 'POST', body: JSON.stringify(body) }),

  // Projects
  getProjects: () => request('/projects'),
  getProject: (id) => request(`/projects/${id}`),
  getProjectTools: (id) => request(`/projects/${id}/tools`),
  createProject: (body) => request('/projects', { method: 'POST', body: JSON.stringify(body) }),

  // Movements
  getMovements: () => request('/movements'),
};
