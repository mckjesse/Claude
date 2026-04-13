import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
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
    const [toolsRes, projectsRes, movementsRes] = await Promise.all([
      supabase.from('tools').select('id, status, current_location_type'),
      supabase.from('projects').select('id, status').eq('status', 'active'),
      supabase
        .from('tool_movements')
        .select('id, tool_id, to_location_type, to_project_id, moved_at, note, tools(name, tool_code), projects:to_project_id(name)')
        .order('moved_at', { ascending: false })
        .limit(5),
    ]);

    const tools = toolsRes.data || [];
    setStats({
      totalTools: tools.length,
      warehouseTools: tools.filter((t) => t.current_location_type === 'warehouse').length,
      assignedTools: tools.filter((t) => t.current_location_type === 'project').length,
      activeProjects: (projectsRes.data || []).length,
      recentMovements: movementsRes.data || [],
    });
    setLoading(false);
  }, []);

  useEffect(() => { fetchStats(); }, [fetchStats]);

  const handleRealtime = useCallback(() => { fetchStats(); }, [fetchStats]);
  useRealtime('tools', handleRealtime);
  useRealtime('tool_movements', handleRealtime);

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
                <td>{m.tools?.name} ({m.tools?.tool_code})</td>
                <td>
                  {m.to_location_type === 'warehouse'
                    ? 'Warehouse'
                    : m.projects?.name || 'Project'}
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
