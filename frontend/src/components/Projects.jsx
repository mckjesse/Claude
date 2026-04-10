import React, { useState, useEffect } from 'react';
import { getProjects, createProject, deleteProject, getTools } from '../api/client';

export default function Projects({ onDataChange, refreshKey }) {
  const [projects, setProjects] = useState([]);
  const [tools, setTools] = useState([]);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);

  const fetchData = () => {
    getProjects().then(setProjects).catch((e) => setError(e.message));
    getTools().then(setTools).catch(() => {});
  };

  useEffect(fetchData, [refreshKey]);

  const handleAdd = async (e) => {
    e?.preventDefault();
    if (!name.trim()) return;
    try {
      await createProject({ name: name.trim() });
      setName('');
      fetchData();
      onDataChange();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteProject(deleteTarget.id);
      setDeleteTarget(null);
      fetchData();
      onDataChange();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <>
      <div className="section-header"><h2>Projects / Sites</h2></div>

      {error && <p style={{ color: 'var(--danger)', marginBottom: 16 }}>{error}</p>}

      <form className="form-row" onSubmit={handleAdd}>
        <div className="form-group" style={{ flex: 1 }}>
          <label>Project Name</label>
          <input type="text" placeholder="e.g. Office Fit Out - Level 3" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <button className="btn btn-primary" type="submit">+ Add Project</button>
      </form>

      {projects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">&#128197;</div>
          <p>No projects created yet.</p>
          <p>Create a project above to start assigning tools.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Project Name</th>
                <th>Tools Assigned</th>
                <th>Created</th>
                <th style={{ width: 100, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => {
                const count = tools.filter((t) => t.project === p.id).length;
                return (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 600, color: 'var(--white)' }}>{p.name}</td>
                    <td>
                      <span style={{ fontWeight: 700, color: 'var(--white)' }}>{count}</span>{' '}
                      <span style={{ color: 'var(--text-dim)' }}>tool{count !== 1 ? 's' : ''}</span>
                    </td>
                    <td style={{ color: 'var(--text-muted)' }}>{new Date(p.created_at).toLocaleDateString()}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button className="btn btn-sm btn-danger" onClick={() => setDeleteTarget(p)}>Delete</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete confirm modal */}
      {deleteTarget && (
        <div className="modal-overlay active" onClick={() => setDeleteTarget(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Confirm Delete</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
              Delete project "{deleteTarget.name}"? Tools assigned here will be returned to the Warehouse.
            </p>
            <div className="modal-actions">
              <button className="btn" onClick={() => setDeleteTarget(null)}>Cancel</button>
              <button className="btn btn-danger" onClick={handleDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
