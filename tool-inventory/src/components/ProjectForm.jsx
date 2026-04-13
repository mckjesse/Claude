import { useState } from 'react';
import { supabase } from '../lib/supabase';

export default function ProjectForm({ onCreated }) {
  const [form, setForm] = useState({ project_code: '', name: '', site_address: '' });
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSaving(true);

    const { error: err } = await supabase.from('projects').insert({
      project_code: form.project_code.trim(),
      name: form.name.trim(),
      site_address: form.site_address.trim() || null,
    });

    setSaving(false);
    if (err) {
      setError(err.message.includes('duplicate') ? 'Project code already exists.' : err.message);
      return;
    }
    setForm({ project_code: '', name: '', site_address: '' });
    onCreated?.();
  };

  return (
    <form onSubmit={handleSubmit} className="inline-form">
      <input
        placeholder="Project code"
        value={form.project_code}
        onChange={(e) => setForm({ ...form, project_code: e.target.value })}
        required
      />
      <input
        placeholder="Project name"
        value={form.name}
        onChange={(e) => setForm({ ...form, name: e.target.value })}
        required
      />
      <input
        placeholder="Site address (optional)"
        value={form.site_address}
        onChange={(e) => setForm({ ...form, site_address: e.target.value })}
      />
      <button type="submit" disabled={saving}>
        {saving ? 'Adding...' : 'Add Project'}
      </button>
      {error && <span className="error">{error}</span>}
    </form>
  );
}
