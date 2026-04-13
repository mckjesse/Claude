import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { useRealtime } from '../hooks/useRealtime';

function locationLabel(type, project) {
  if (type === 'warehouse') return 'Warehouse';
  return project?.name || 'Project';
}

export default function MovementHistory() {
  const [movements, setMovements] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchMovements = useCallback(async () => {
    const { data } = await supabase
      .from('tool_movements')
      .select(`
        *,
        tools(name, tool_code),
        from_project:from_project_id(name),
        to_project:to_project_id(name)
      `)
      .order('moved_at', { ascending: false })
      .limit(100);

    setMovements(data || []);
    setLoading(false);
  }, []);

  useEffect(() => { fetchMovements(); }, [fetchMovements]);

  const handleRealtime = useCallback(() => { fetchMovements(); }, [fetchMovements]);
  useRealtime('tool_movements', handleRealtime);

  if (loading) return <p>Loading...</p>;

  return (
    <div>
      <h1>Movement History</h1>

      {movements.length === 0 ? (
        <p className="empty">No movement records yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Tool</th>
              <th>From</th>
              <th>To</th>
              <th>Moved By</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {movements.map((m) => (
              <tr key={m.id}>
                <td>{new Date(m.moved_at).toLocaleString()}</td>
                <td>{m.tools?.name} ({m.tools?.tool_code})</td>
                <td>{locationLabel(m.from_location_type, m.from_project)}</td>
                <td>{locationLabel(m.to_location_type, m.to_project)}</td>
                <td>{m.moved_by || '—'}</td>
                <td>{m.note || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
