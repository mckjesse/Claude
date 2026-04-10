import React, { useState, useEffect } from 'react';
import { getTools, getProjects, allocateTool } from '../api/client';

export default function Allocations({ onDataChange, refreshKey }) {
  const [tools, setTools] = useState([]);
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState('');

  const fetchData = () => {
    getTools().then(setTools).catch((e) => setError(e.message));
    getProjects().then(setProjects).catch(() => {});
  };

  useEffect(fetchData, [refreshKey]);

  const handleAllocate = async (toolId, value) => {
    const projectId = value === '' ? null : parseInt(value, 10);
    try {
      await allocateTool(toolId, projectId);
      fetchData();
      onDataChange();
    } catch (err) {
      setError(err.message);
    }
  };

  if (tools.length === 0) {
    return (
      <>
        <div className="section-header"><h2>Assign &amp; Return Tools</h2></div>
        <div className="empty-state">
          <div className="empty-icon">&#128295;</div>
          <p>Add tools and projects first to manage allocations.</p>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="section-header"><h2>Assign &amp; Return Tools</h2></div>

      {error && <p style={{ color: 'var(--danger)', marginBottom: 16 }}>{error}</p>}

      <p style={{ color: 'var(--text-muted)', marginBottom: 24, fontSize: 14 }}>
        Change where each tool is allocated. Select a project to assign it on-site, or choose <strong>Warehouse</strong> to return it.
      </p>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Tool Name</th>
              <th>Type</th>
              <th>Current Location</th>
              <th>Assign To</th>
            </tr>
          </thead>
          <tbody>
            {tools.map((t) => (
              <tr key={t.id}>
                <td style={{ fontWeight: 600, color: 'var(--white)' }}>{t.name}</td>
                <td>
                  <span className={`badge ${t.type === 'plant' ? 'badge-plant' : 'badge-equipment'}`}>
                    {t.type === 'plant' ? 'Plant' : 'Equipment'}
                  </span>
                </td>
                <td>
                  <span className={`badge ${t.status === 'assigned' ? 'badge-assigned' : 'badge-warehouse'}`}>
                    <span className="badge-dot" />{t.location}
                  </span>
                </td>
                <td>
                  <select
                    className="allocation-select"
                    value={t.project ?? ''}
                    onChange={(e) => handleAllocate(t.id, e.target.value)}
                  >
                    <option value="">Warehouse</option>
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
