import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';

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
      supabase
        .from('projects')
        .select('id, name, project_code')
        .eq('status', 'active')
        .order('name')
        .then(({ data }) => setProjects(data || []));
    }
  }, [isReturn]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const toLocationType = isReturn ? 'warehouse' : 'project';
    const toProjectId = isReturn ? null : selectedProjectId;

    // Insert movement record
    const { error: moveErr } = await supabase.from('tool_movements').insert({
      tool_id: tool.id,
      from_location_type: tool.current_location_type,
      from_project_id: tool.current_project_id,
      to_location_type: toLocationType,
      to_project_id: toProjectId,
      moved_by: movedBy.trim() || null,
      note: note.trim() || null,
    });

    if (moveErr) {
      setError(moveErr.message);
      setSaving(false);
      return;
    }

    // Update tool location
    const { error: updateErr } = await supabase
      .from('tools')
      .update({
        current_location_type: toLocationType,
        current_project_id: toProjectId,
        status: isReturn ? 'available' : 'assigned',
      })
      .eq('id', tool.id);

    if (updateErr) {
      setError(updateErr.message);
      setSaving(false);
      return;
    }

    setSaving(false);
    onDone?.();
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
                {projects.map((p) => (
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
