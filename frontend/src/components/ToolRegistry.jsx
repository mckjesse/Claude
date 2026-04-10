import React, { useState, useEffect, useRef } from 'react';
import { getTools, createTool, deleteTool, bulkImportTools } from '../api/client';

export default function ToolRegistry({ onDataChange, refreshKey }) {
  const [tools, setTools] = useState([]);
  const [name, setName] = useState('');
  const [type, setType] = useState('plant');
  const [error, setError] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);

  // CSV state
  const fileRef = useRef();
  const [csvPreview, setCsvPreview] = useState(null); // { rows: [...], newCount, dupCount }
  const [importing, setImporting] = useState(false);

  const fetchTools = () => {
    getTools().then(setTools).catch((e) => setError(e.message));
  };

  useEffect(fetchTools, [refreshKey]);

  const handleAdd = async (e) => {
    e?.preventDefault();
    if (!name.trim()) return;
    try {
      await createTool({ name: name.trim(), type });
      setName('');
      fetchTools();
      onDataChange();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteTool(deleteTarget.id);
      setDeleteTarget(null);
      fetchTools();
      onDataChange();
    } catch (err) {
      setError(err.message);
    }
  };

  // ---- CSV Upload ----
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      const lines = ev.target.result.split(/\r?\n/).filter((l) => l.trim());
      let startIdx = 0;
      if (lines.length > 0 && lines[0].toLowerCase().includes('name')) startIdx = 1;

      const existingNames = new Set(tools.map((t) => t.name.toLowerCase()));
      const rows = [];

      for (let i = startIdx; i < lines.length; i++) {
        const cols = lines[i].split(',').map((c) => c.trim().replace(/^"|"$/g, ''));
        if (!cols[0]) continue;
        const toolName = cols[0];
        let toolType = 'equipment';
        if (cols[1]) {
          const t = cols[1].toLowerCase().trim();
          if (t === 'plant' || t === 'p') toolType = 'plant';
        }
        const duplicate = existingNames.has(toolName.toLowerCase());
        rows.push({ name: toolName, type: toolType, duplicate });
      }

      const newCount = rows.filter((r) => !r.duplicate).length;
      const dupCount = rows.filter((r) => r.duplicate).length;
      setCsvPreview({ rows, newCount, dupCount });
    };
    reader.readAsText(file);
    if (fileRef.current) fileRef.current.value = '';
  };

  const handleCsvImport = async () => {
    if (!csvPreview) return;
    setImporting(true);
    try {
      const toImport = csvPreview.rows.filter((r) => !r.duplicate).map((r) => ({ name: r.name, type: r.type }));
      await bulkImportTools(toImport);
      setCsvPreview(null);
      fetchTools();
      onDataChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <>
      <div className="section-header"><h2>Tool Registry</h2></div>

      {error && <p style={{ color: 'var(--danger)', marginBottom: 16 }}>{error}</p>}

      {/* Add tool form */}
      <form className="form-row" onSubmit={handleAdd}>
        <div className="form-group" style={{ flex: 1 }}>
          <label>Tool Name</label>
          <input type="text" placeholder="e.g. Hilti Drill #4" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Type</label>
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="plant">Plant</option>
            <option value="equipment">Equipment</option>
          </select>
        </div>
        <button className="btn btn-primary" type="submit">+ Add Tool</button>
        <span style={{ color: 'var(--text-dim)', fontSize: 13, paddingBottom: 10 }}>or</span>
        <input type="file" ref={fileRef} accept=".csv" style={{ display: 'none' }} onChange={handleFileSelect} />
        <button className="btn" type="button" onClick={() => fileRef.current?.click()}>&#8593; Upload CSV</button>
      </form>

      {/* CSV Preview */}
      {csvPreview && (
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: '20px 24px', marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--white)' }}>CSV Preview</h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-sm" onClick={() => setCsvPreview(null)}>Cancel</button>
              <button className="btn btn-sm btn-primary" onClick={handleCsvImport} disabled={importing}>
                {importing ? 'Importing...' : 'Import All'}
              </button>
            </div>
          </div>
          <p style={{ color: 'var(--text-dim)', fontSize: 12, marginBottom: 12 }}>
            Expected format: <strong>Name, Type</strong> (type = plant or equipment). First row is treated as a header if it contains "name".
          </p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Tool Name</th><th>Type</th><th>Status</th></tr></thead>
              <tbody>
                {csvPreview.rows.map((r, i) => (
                  <tr key={i} style={r.duplicate ? { opacity: 0.5 } : undefined}>
                    <td style={{ fontWeight: 600, color: 'var(--white)' }}>{r.name}</td>
                    <td><span className={`badge ${r.type === 'plant' ? 'badge-plant' : 'badge-equipment'}`}>{r.type === 'plant' ? 'Plant' : 'Equipment'}</span></td>
                    <td>{r.duplicate
                      ? <span style={{ color: 'var(--warning)', fontWeight: 600 }}>Duplicate</span>
                      : <span style={{ color: 'var(--success)' }}>Ready</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 12 }}>
            {csvPreview.newCount} new tool{csvPreview.newCount !== 1 ? 's' : ''} to import
            {csvPreview.dupCount > 0 && ` (${csvPreview.dupCount} duplicate${csvPreview.dupCount !== 1 ? 's' : ''} will be skipped)`}
          </p>
        </div>
      )}

      {/* Tools table */}
      {tools.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">&#9881;</div>
          <p>No tools registered yet.</p>
          <p>Add your first tool above to get started.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Tool Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Location</th>
                <th style={{ width: 100, textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tools.map((t) => (
                <tr key={t.id}>
                  <td style={{ fontWeight: 600, color: 'var(--white)' }}>{t.name}</td>
                  <td><span className={`badge ${t.type === 'plant' ? 'badge-plant' : 'badge-equipment'}`}>{t.type === 'plant' ? 'Plant' : 'Equipment'}</span></td>
                  <td>
                    <span className={`badge ${t.status === 'assigned' ? 'badge-assigned' : 'badge-warehouse'}`}>
                      <span className="badge-dot" />{t.status === 'assigned' ? 'Assigned' : 'Warehouse'}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{t.location}</td>
                  <td style={{ textAlign: 'right' }}>
                    <button className="btn btn-sm btn-danger" onClick={() => setDeleteTarget(t)}>Delete</button>
                  </td>
                </tr>
              ))}
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
              Delete tool "{deleteTarget.name}"? This will remove it from all allocations.
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
