import { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { useRealtime } from '../hooks/useRealtime';
import ToolForm from '../components/ToolForm';
import AssignReturnModal from '../components/AssignReturnModal';

export default function Tools() {
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalTool, setModalTool] = useState(null);
  const [searchParams] = useSearchParams();
  const locationFilter = searchParams.get('location');

  const fetchTools = useCallback(async () => {
    const data = await api.getTools(locationFilter);
    setTools(data);
    setLoading(false);
  }, [locationFilter]);

  useEffect(() => { fetchTools(); }, [fetchTools]);

  const refresh = useCallback(() => { fetchTools(); }, [fetchTools]);
  useRealtime('tools', refresh);

  if (loading) return <p>Loading...</p>;

  return (
    <div>
      <h1>
        Tools
        {locationFilter === 'warehouse' && ' — Warehouse'}
        {locationFilter === 'project' && ' — On Projects'}
      </h1>

      <ToolForm onCreated={fetchTools} />

      {tools.length === 0 ? (
        <p className="empty">No tools found.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Category</th>
              <th>Location</th>
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
                  {tool.current_location_type === 'warehouse'
                    ? 'Warehouse'
                    : tool.project_name || 'Project'}
                </td>
                <td>
                  {tool.current_location_type === 'warehouse' ? (
                    <button className="btn-sm" onClick={() => setModalTool(tool)}>
                      Assign
                    </button>
                  ) : (
                    <button className="btn-sm btn-secondary" onClick={() => setModalTool(tool)}>
                      Return
                    </button>
                  )}
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
            fetchTools();
          }}
        />
      )}
    </div>
  );
}
