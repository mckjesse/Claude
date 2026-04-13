import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import ProjectForm from '../components/ProjectForm';

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchProjects = useCallback(async () => {
    const data = await api.getProjects();
    setProjects(data);
    setLoading(false);
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  if (loading) return <p>Loading...</p>;

  return (
    <div>
      <h1>Projects</h1>

      <ProjectForm onCreated={fetchProjects} />

      {projects.length === 0 ? (
        <p className="empty">No projects yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Site Address</th>
              <th>Status</th>
              <th>Tools Assigned</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.id}>
                <td>{p.project_code}</td>
                <td>{p.name}</td>
                <td>{p.site_address || '—'}</td>
                <td className="capitalize">{p.status.replace('_', ' ')}</td>
                <td>{p.tool_count}</td>
                <td>
                  <Link to={`/projects/${p.id}`} className="btn-sm">
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
