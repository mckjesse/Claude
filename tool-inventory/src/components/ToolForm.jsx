import { useState } from 'react';
import { api } from '../lib/api';

export default function ToolForm({ onCreated }) {
  const [form, setForm] = useState({ tool_code: '', name: '', category: 'equipment' });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);

    try {
      await api.createTool(form);
      setForm({ tool_code: '', name: '', category: 'equipment' });
      onCreated?.();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="inline-form">
      <input
        placeholder="Tool code"
        value={form.tool_code}
        onChange={(e) => setForm({ ...form, tool_code: e.target.value })}
        required
      />
      <input
        placeholder="Tool name"
        value={form.name}
        onChange={(e) => setForm({ ...form, name: e.target.value })}
        required
      />
      <select
        value={form.category}
        onChange={(e) => setForm({ ...form, category: e.target.value })}
      >
        <option value="equipment">Equipment</option>
        <option value="plant">Plant</option>
      </select>
      <button type="submit" disabled={saving}>
        {saving ? 'Adding...' : 'Add Tool'}
      </button>
      {error && <span className="error">{error}</span>}
    </form>
  );
}
