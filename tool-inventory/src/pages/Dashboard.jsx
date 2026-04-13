import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { useRealtime } from '../hooks/useRealtime';

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalTools: 0,
    warehouseTools: 0,
    assignedTools: 0,
    activeProjects: 0,
    recentMovements: [],
  });
  const [loading, setLoading] = useState(true);

  const fetchStats = useCallback(async () => {
    const data = await api.getStats();
    setStats(data);
    setLoading(false);
  }, []);

  useEffect(() => { fetchStats(); }, [fetchStats]);

  const refresh = useCallback(() => { fetchStats(); }, [fetchStats]);
  useRealtime('tools', refresh);
  useRealtime('movements', refresh);

  if (loading) return <p>Loading...</p>;

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="card-grid">
        <Link to="/tools" className="card">
          <h3>Total Tools</h3>
          <p className="card-number">{stats.totalTools}</p>
        </Link>
        <Link to="/tools?location=warehouse" className="card">
          <h3>In Warehouse</h3>
          <p className="card-number">{stats.warehouseTools}</p>
        </Link>
        <Link to="/tools?location=project" className="card">
          <h3>On Projects</h3>
          <p className="card-number">{stats.assignedTools}</p>
        </Link>
        <Link to="/projects" className="card">
          <h3>Active Projects</h3>
          <p className="card-number">{stats.activeProjects}</p>
        </Link>
      </div>

      <h2>Recent Movements</h2>
      {stats.recentMovements.length === 0 ? (
        <p className="empty">No movements yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Tool</th>
              <th>Moved To</th>
              <th>When</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {stats.recentMovements.map((m) => (
              <tr key={m.id}>
                <td>{m.tool_name} ({m.tool_code})</td>
                <td>
                  {m.to_location_type === 'warehouse'
                    ? 'Warehouse'
                    : m.to_project_name || 'Project'}
                </td>
                <td>{new Date(m.moved_at).toLocaleString()}</td>
                <td>{m.note || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
