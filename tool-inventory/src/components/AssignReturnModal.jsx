import { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function AssignReturnModal({ tool, onClose, onDone }) {
  const [projects, setProjects] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState('');
  const [movedBy, setMovedBy] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const isReturn = tool.current_location_type === 'project';

  useEffect(() => {
    if (!isReturn) {
      api.getProjects().then(setProjects);
    }
  }, [isReturn]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      if (isReturn) {
        await api.returnTool(tool.id, {
          moved_by: movedBy.trim() || null,
          note: note.trim() || null,
        });
      } else {
        await api.assignTool(tool.id, {
          project_id: Number(selectedProjectId),
          moved_by: movedBy.trim() || null,
          note: note.trim() || null,
        });
      }
      onDone?.();
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{isReturn ? 'Return to Warehouse' : 'Assign to Project'}</h3>
        <p>
          <strong>{tool.name}</strong> ({tool.tool_code})
        </p>
        <form onSubmit={handleSubmit}>
          {!isReturn && (
            <label>
              Project
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                required
              >
                <option value="">Select a project...</option>
                {projects
                  .filter((p) => p.status === 'active')
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.project_code})
                    </option>
                  ))}
              </select>
            </label>
          )}
          <label>
            Moved by
            <input
              placeholder="Name (optional)"
              value={movedBy}
              onChange={(e) => setMovedBy(e.target.value)}
            />
          </label>
          <label>
            Note
            <input
              placeholder="Optional note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={saving}>
              {saving ? 'Saving...' : isReturn ? 'Return' : 'Assign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
