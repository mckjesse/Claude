import { useState } from 'react';
import { supabase } from '../lib/supabase';

export default function ToolForm({ onCreated }) {
  const [form, setForm] = useState({ tool_code: '', name: '', category: 'equipment' });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);

    const { error: err } = await supabase.from('tools').insert({
      tool_code: form.tool_code.trim(),
      name: form.name.trim(),
      category: form.category,
    });

    setSaving(false);
    if (err) {
      setError(err.message.includes('duplicate') ? 'Tool code already exists.' : err.message);
      return;
    }
    setForm({ tool_code: '', name: '', category: 'equipment' });
    onCreated?.();
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
