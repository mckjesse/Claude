import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import { useRealtime } from '../hooks/useRealtime';

function locationLabel(type, projectName) {
  if (type === 'warehouse') return 'Warehouse';
  return projectName || 'Project';
}

export default function MovementHistory() {
  const [movements, setMovements] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchMovements = useCallback(async () => {
    const data = await api.getMovements();
    setMovements(data);
    setLoading(false);
  }, []);

  useEffect(() => { fetchMovements(); }, [fetchMovements]);

  const refresh = useCallback(() => { fetchMovements(); }, [fetchMovements]);
  useRealtime('movements', refresh);

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
                <td>{m.tool_name} ({m.tool_code})</td>
                <td>{locationLabel(m.from_location_type, m.from_project_name)}</td>
                <td>{locationLabel(m.to_location_type, m.to_project_name)}</td>
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
