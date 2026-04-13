import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { useRealtime } from '../hooks/useRealtime';
import AssignReturnModal from '../components/AssignReturnModal';

export default function ProjectDetail() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalTool, setModalTool] = useState(null);

  const fetchData = useCallback(async () => {
    const [projectRes, toolsRes] = await Promise.all([
      supabase.from('projects').select('*').eq('id', id).single(),
      supabase
        .from('tools')
        .select('*')
        .eq('current_project_id', id)
        .order('name'),
    ]);

    setProject(projectRes.data);
    setTools(toolsRes.data || []);
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleRealtime = useCallback(() => { fetchData(); }, [fetchData]);
  useRealtime('tools', handleRealtime);

  if (loading) return <p>Loading...</p>;
  if (!project) return <p>Project not found.</p>;

  return (
    <div>
      <Link to="/projects" className="back-link">&larr; All Projects</Link>
      <h1>{project.name}</h1>
      <div className="project-meta">
        <span><strong>Code:</strong> {project.project_code}</span>
        <span><strong>Status:</strong> <span className="capitalize">{project.status.replace('_', ' ')}</span></span>
        {project.site_address && (
          <span><strong>Site:</strong> {project.site_address}</span>
        )}
      </div>

      <h2>Allocated Tools ({tools.length})</h2>

      {tools.length === 0 ? (
        <p className="empty">No tools assigned to this project.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Category</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tools.map((tool) => (
              <tr key={tool.id}>
                <td>{tool.tool_code}</td>
                <td>{tool.name}</td>
                <td className="capitalize">{tool.category}</td>
                <td>
                  <button
                    className="btn-sm btn-secondary"
                    onClick={() => setModalTool(tool)}
                  >
                    Return to Warehouse
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {modalTool && (
        <AssignReturnModal
          tool={modalTool}
          onClose={() => setModalTool(null)}
          onDone={() => {
            setModalTool(null);
            fetchData();
          }}
        />
      )}
    </div>
  );
}
