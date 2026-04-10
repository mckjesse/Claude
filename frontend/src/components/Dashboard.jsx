import React, { useState, useEffect } from 'react';
import { getDashboard } from '../api/client';

export default function Dashboard({ refreshKey }) {
  const [data, setData] = useState(null);
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((e) => setError(e.message));
  }, [refreshKey]);

  const toggle = (id) => setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));

  if (error) return <div className="empty-state"><p>Error loading dashboard: {error}</p></div>;
  if (!data) return <div className="empty-state"><p>Loading...</p></div>;

  const { stats, warehouse, projects } = data;

  // Filter cards by search
  const q = search.toLowerCase();
  const matchesSearch = (card) => {
    if (!q) return true;
    if (card.name.toLowerCase().includes(q)) return true;
    return card.tools.some((t) => t.name.toLowerCase().includes(q));
  };

  const allCards = [
    { ...warehouse, id: 'warehouse', isWarehouse: true },
    ...projects.map((p) => ({ ...p, isWarehouse: false })),
  ].filter(matchesSearch);

  return (
    <>
      {/* Stats */}
      <div className="stats-bar">
        <div className="stat-card">
          <span className="stat-label">Total Tools</span>
          <span className="stat-value">{stats.total_tools}</span>
          <span className="stat-sub">{stats.plant_count} plant &middot; {stats.equipment_count} equipment</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">In Warehouse</span>
          <span className="stat-value" style={{ color: 'var(--success)' }}>{stats.warehouse_count}</span>
          <span className="stat-sub">Available for allocation</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Assigned to Sites</span>
          <span className="stat-value" style={{ color: 'var(--blue)' }}>{stats.assigned_count}</span>
          <span className="stat-sub">Across {stats.project_count} project{stats.project_count !== 1 ? 's' : ''}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Active Projects</span>
          <span className="stat-value">{stats.project_count}</span>
          <span className="stat-sub">Sites tracked</span>
        </div>
      </div>

      {/* Search + Grid */}
      <div className="section-header">
        <h2>Project Dashboard</h2>
        <input
          type="text"
          className="search-input"
          placeholder="Search projects or tools..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {allCards.length === 0 && stats.total_tools === 0 && stats.project_count === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">&#128736;</div>
          <p>Welcome to Tool Inventory!</p>
          <p>Start by adding tools and creating projects using the tabs above.</p>
        </div>
      ) : allCards.length === 0 ? (
        <div className="empty-state"><p>No results match your search.</p></div>
      ) : (
        <div className="project-grid">
          {allCards.map((card) => {
            const tools = q
              ? card.tools.filter((t) => t.name.toLowerCase().includes(q) || card.name.toLowerCase().includes(q))
              : card.tools;
            const plantCount = tools.filter((t) => t.type === 'plant').length;
            const equipCount = tools.filter((t) => t.type === 'equipment').length;
            const isOpen = expanded[card.id];

            return (
              <div key={card.id} className={`project-card${card.isWarehouse ? ' warehouse-card' : ''}${isOpen ? ' expanded' : ''}`}>
                <div className="project-card-header" onClick={() => toggle(card.id)}>
                  <div>
                    <div className="project-card-title">
                      {card.isWarehouse ? '\u{1F3E2} ' : '\u{1F4CD} '}{card.name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 2 }}>
                      {plantCount} plant &middot; {equipCount} equipment
                    </div>
                  </div>
                  <div className="project-card-meta">
                    <span className="project-card-count">
                      <strong>{tools.length}</strong> tool{tools.length !== 1 ? 's' : ''}
                    </span>
                    <span className="expand-arrow">&#9660;</span>
                  </div>
                </div>
                <div className="project-card-body">
                  <div className="project-card-body-inner">
                    {tools.length === 0 ? (
                      <p style={{ color: 'var(--text-dim)', fontSize: 13, padding: '16px 0' }}>No tools currently here.</p>
                    ) : (
                      tools.map((t) => (
                        <div key={t.id} className="tool-list-item">
                          <div className="tool-list-item-info">
                            <span className="tool-list-item-name">{t.name}</span>
                            <span className={`badge ${t.type === 'plant' ? 'badge-plant' : 'badge-equipment'}`} style={{ fontSize: 10 }}>
                              {t.type === 'plant' ? 'Plant' : 'Equipment'}
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
