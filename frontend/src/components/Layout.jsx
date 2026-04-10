import React, { useState } from 'react';
import Dashboard from './Dashboard';
import ToolRegistry from './ToolRegistry';
import Projects from './Projects';
import Allocations from './Allocations';

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'tools', label: 'Tools' },
  { id: 'projects', label: 'Projects' },
  { id: 'allocations', label: 'Allocations' },
];

export default function Layout({ userName, onLogout }) {
  const [activeTab, setActiveTab] = useState('dashboard');
  // Global refresh trigger — bumped when data changes so other tabs re-fetch
  const [refreshKey, setRefreshKey] = useState(0);
  const triggerRefresh = () => setRefreshKey((k) => k + 1);

  return (
    <>
      {/* Header */}
      <header className="header">
        <div className="header-brand">
          <svg width="44" height="44" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="0" width="200" height="200" fill="#ffffff" />
            <rect x="10" y="10" width="180" height="180" fill="#000000" />
            <path d="M30,25 L80,25 L80,40 L52,40 L52,55 L75,55 L75,70 L52,70 L52,90 L36,90 L36,40 L30,40 Z" fill="#ffffff" />
            <circle cx="140" cy="57" r="33" fill="#ffffff" />
            <circle cx="140" cy="57" r="17" fill="#000000" />
            <path d="M28,110 L44,110 L55,127 L66,110 L82,110 L65,137 L82,164 L66,164 L55,147 L44,164 L28,164 L45,137 Z" fill="#ffffff" />
            <path d="M108,110 L145,110 C166,110 178,124 178,137 C178,150 166,164 145,164 L108,164 Z M124,126 L124,148 L143,148 C153,148 160,144 160,137 C160,130 153,126 143,126 Z" fill="#ffffff" />
          </svg>
          <div className="divider" />
          <span className="app-title">Tool Inventory</span>
        </div>
        <div className="header-user">
          <span className="user-name">{userName}</span>
          <button className="btn btn-sm" onClick={onLogout}>Sign out</button>
        </div>
      </header>

      {/* Nav */}
      <nav className="nav-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`nav-tab${activeTab === tab.id ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Pages */}
      <main className="main">
        {activeTab === 'dashboard' && <Dashboard refreshKey={refreshKey} />}
        {activeTab === 'tools' && <ToolRegistry onDataChange={triggerRefresh} refreshKey={refreshKey} />}
        {activeTab === 'projects' && <Projects onDataChange={triggerRefresh} refreshKey={refreshKey} />}
        {activeTab === 'allocations' && <Allocations onDataChange={triggerRefresh} refreshKey={refreshKey} />}
      </main>
    </>
  );
}
