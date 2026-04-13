// ── State ──
let data = { tools: [], projects: [], history: [] };
let pendingMove = null; // {toolId, projectId} for move modal

// ── API ──
const API = '/api/data';

async function loadData() {
  try {
    const res = await fetch(API);
    if (res.ok) data = await res.json();
  } catch (e) {
    console.error('Failed to load data', e);
  }
  render();
}

async function saveData(action, payload) {
  try {
    const res = await fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, ...payload }),
    });
    if (res.ok) data = await res.json();
  } catch (e) {
    console.error('Save failed', e);
  }
  render();
}

// ── Tabs ──
document.querySelectorAll('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('page-' + tab.dataset.page).classList.add('active');
  });
});

// ── Render ──
function render() {
  renderDashboard();
  renderTools();
  renderProjects();
  renderAllocations();
  renderHistory();
}

// ── Dashboard ──
function renderDashboard() {
  const warehouseTools = data.tools.filter(t => !t.projectId);
  const assignedTools = data.tools.filter(t => t.projectId);

  document.getElementById('stat-total').textContent = data.tools.length;
  document.getElementById('stat-warehouse').textContent = warehouseTools.length;
  document.getElementById('stat-assigned').textContent = assignedTools.length;
  document.getElementById('stat-projects').textContent = data.projects.length;

  const search = (document.getElementById('dashboard-search').value || '').toLowerCase();
  const container = document.getElementById('dashboard-cards');

  // Build cards: one for warehouse + one per project
  let html = '';

  // Warehouse card
  const wTools = warehouseTools.filter(t =>
    !search || t.name.toLowerCase().includes(search) || t.toolCode.toLowerCase().includes(search) || 'warehouse'.includes(search)
  );
  if (!search || wTools.length > 0 || 'warehouse'.includes(search)) {
    html += buildCard('Warehouse', wTools);
  }

  // Project cards
  data.projects.forEach(p => {
    const pTools = data.tools
      .filter(t => t.projectId === p.id)
      .filter(t => !search || t.name.toLowerCase().includes(search) || t.toolCode.toLowerCase().includes(search) || p.name.toLowerCase().includes(search));
    if (!search || pTools.length > 0 || p.name.toLowerCase().includes(search)) {
      html += buildCard(p.name, pTools, p.projectCode);
    }
  });

  container.innerHTML = html;

  // Toggle expand
  container.querySelectorAll('.project-card-header').forEach(h => {
    h.addEventListener('click', () => h.closest('.project-card').classList.toggle('expanded'));
  });
}

function buildCard(name, tools, code) {
  const sub = code ? `<span style="color:var(--text-muted);font-size:0.8rem;margin-left:0.5rem">${code}</span>` : '';
  let toolRows = '';
  if (tools.length === 0) {
    toolRows = '<div style="color:var(--text-muted);font-size:0.85rem;padding:0.25rem 0">No tools</div>';
  } else {
    tools.forEach(t => {
      toolRows += `<div class="tool-row">
        <span>${t.name} <span style="color:var(--text-muted)">(${t.toolCode})</span></span>
        <span class="badge badge-${t.type}">${t.type}</span>
      </div>`;
    });
  }
  return `<div class="project-card">
    <div class="project-card-header">
      <span class="project-card-name">${name}${sub}</span>
      <span class="project-card-count">${tools.length} tool${tools.length !== 1 ? 's' : ''}</span>
    </div>
    <div class="project-card-body">${toolRows}</div>
  </div>`;
}

document.getElementById('dashboard-search').addEventListener('input', renderDashboard);

// ── Tools ──
function renderTools() {
  const tbody = document.getElementById('tools-tbody');
  const empty = document.getElementById('tools-empty');

  if (data.tools.length === 0) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  tbody.innerHTML = data.tools.map(t => {
    const loc = t.projectId
      ? (data.projects.find(p => p.id === t.projectId)?.name || 'Project')
      : 'Warehouse';
    const locBadge = t.projectId ? 'badge-assigned' : 'badge-warehouse';
    return `<tr>
      <td>${t.toolCode}</td>
      <td>${t.name}</td>
      <td><span class="badge badge-${t.type}">${t.type}</span></td>
      <td><span class="badge ${locBadge}">${loc}</span></td>
      <td><button class="btn-icon btn-sm" onclick="deleteTool('${t.id}')" title="Delete">&#x2715;</button></td>
    </tr>`;
  }).join('');
}

document.getElementById('tool-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const toolCode = document.getElementById('tool-code').value.trim();
  const name = document.getElementById('tool-name').value.trim();
  const type = document.getElementById('tool-type').value;
  if (!toolCode || !name) return;

  await saveData('addTool', { toolCode, name, type });
  document.getElementById('tool-code').value = '';
  document.getElementById('tool-name').value = '';
});

window.deleteTool = function(id) {
  showConfirmModal('Delete this tool? Movement history will be preserved.', async () => {
    await saveData('deleteTool', { id });
  });
};

// ── Projects ──
function renderProjects() {
  const tbody = document.getElementById('projects-tbody');
  const empty = document.getElementById('projects-empty');

  if (data.projects.length === 0) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  tbody.innerHTML = data.projects.map(p => {
    const toolCount = data.tools.filter(t => t.projectId === p.id).length;
    return `<tr>
      <td>${p.projectCode}</td>
      <td>${p.name}</td>
      <td>${p.siteAddress || '—'}</td>
      <td>${toolCount}</td>
      <td>${new Date(p.createdAt).toLocaleDateString()}</td>
      <td><button class="btn-icon btn-sm" onclick="deleteProject('${p.id}')" title="Delete">&#x2715;</button></td>
    </tr>`;
  }).join('');
}

document.getElementById('project-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const projectCode = document.getElementById('project-code').value.trim();
  const name = document.getElementById('project-name').value.trim();
  const siteAddress = document.getElementById('project-address').value.trim();
  if (!projectCode || !name) return;

  await saveData('addProject', { projectCode, name, siteAddress });
  document.getElementById('project-code').value = '';
  document.getElementById('project-name').value = '';
  document.getElementById('project-address').value = '';
});

window.deleteProject = function(id) {
  const toolCount = data.tools.filter(t => t.projectId === id).length;
  const msg = toolCount > 0
    ? `Delete this project? ${toolCount} tool(s) will be returned to warehouse.`
    : 'Delete this project?';
  showConfirmModal(msg, async () => {
    await saveData('deleteProject', { id });
  });
};

// ── Allocations ──
function renderAllocations() {
  const tbody = document.getElementById('allocations-tbody');
  const empty = document.getElementById('allocations-empty');

  if (data.tools.length === 0) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  tbody.innerHTML = data.tools.map(t => {
    const currentLoc = t.projectId
      ? (data.projects.find(p => p.id === t.projectId)?.name || 'Project')
      : 'Warehouse';
    const locBadge = t.projectId ? 'badge-assigned' : 'badge-warehouse';

    let options = '<option value="">— Move to —</option>';
    if (t.projectId) {
      options += '<option value="warehouse">Warehouse</option>';
    }
    data.projects.forEach(p => {
      if (p.id !== t.projectId) {
        options += `<option value="${p.id}">${p.name}</option>`;
      }
    });

    return `<tr>
      <td>${t.toolCode}</td>
      <td>${t.name}</td>
      <td><span class="badge badge-${t.type}">${t.type}</span></td>
      <td><span class="badge ${locBadge}">${currentLoc}</span></td>
      <td><select class="allocation-select" onchange="onAllocate('${t.id}', this.value, this)">${options}</select></td>
    </tr>`;
  }).join('');
}

window.onAllocate = function(toolId, value, selectEl) {
  if (!value) return;
  const projectId = value === 'warehouse' ? null : value;
  pendingMove = { toolId, projectId };

  const tool = data.tools.find(t => t.id === toolId);
  const dest = projectId ? data.projects.find(p => p.id === projectId)?.name : 'Warehouse';
  document.getElementById('move-modal-title').textContent = `Move ${tool.name} → ${dest}`;
  document.getElementById('move-by').value = '';
  document.getElementById('move-note').value = '';
  document.getElementById('move-modal').classList.add('active');

  // Reset the select in case they cancel
  selectEl.value = '';
};

document.getElementById('move-confirm').addEventListener('click', async () => {
  if (!pendingMove) return;
  const movedBy = document.getElementById('move-by').value.trim();
  const note = document.getElementById('move-note').value.trim();
  document.getElementById('move-modal').classList.remove('active');

  await saveData('moveTool', {
    toolId: pendingMove.toolId,
    projectId: pendingMove.projectId,
    movedBy: movedBy || null,
    note: note || null,
  });
  pendingMove = null;
});

document.getElementById('move-cancel').addEventListener('click', () => {
  document.getElementById('move-modal').classList.remove('active');
  pendingMove = null;
});

// ── History ──
function renderHistory() {
  const tbody = document.getElementById('history-tbody');
  const empty = document.getElementById('history-empty');

  if (data.history.length === 0) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  // Show newest first
  const sorted = [...data.history].reverse();
  tbody.innerHTML = sorted.map(h => `<tr>
    <td>${new Date(h.date).toLocaleString()}</td>
    <td>${h.toolName} <span style="color:var(--text-muted)">(${h.toolCode || ''})</span></td>
    <td>${h.from}</td>
    <td>${h.to}</td>
    <td>${h.movedBy || '—'}</td>
    <td>${h.note || '—'}</td>
  </tr>`).join('');
}

// ── Confirm Modal ──
let confirmCallback = null;

function showConfirmModal(message, onConfirm) {
  document.getElementById('modal-message').textContent = message;
  document.getElementById('modal').classList.add('active');
  confirmCallback = onConfirm;
}

document.getElementById('modal-confirm').addEventListener('click', async () => {
  document.getElementById('modal').classList.remove('active');
  if (confirmCallback) await confirmCallback();
  confirmCallback = null;
});

document.getElementById('modal-cancel').addEventListener('click', () => {
  document.getElementById('modal').classList.remove('active');
  confirmCallback = null;
});

// ── CSV Upload ──
let csvRows = []; // parsed rows ready to import

document.getElementById('csv-file').addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (!file) return;
  e.target.value = ''; // reset so same file can be re-selected

  const reader = new FileReader();
  reader.onload = (ev) => {
    const text = ev.target.result;
    parseAndPreviewCSV(text);
  };
  reader.readAsText(file);
});

function parseAndPreviewCSV(text) {
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  if (lines.length < 2) {
    alert('CSV file is empty or has no data rows.');
    return;
  }

  // Parse header to find column indices
  const header = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/['"]/g, ''));
  const codeIdx = header.findIndex(h => h === 'tool_code' || h === 'toolcode' || h === 'code');
  const nameIdx = header.findIndex(h => h === 'name' || h === 'tool_name' || h === 'toolname');
  const typeIdx = header.findIndex(h => h === 'type' || h === 'category');

  if (codeIdx === -1 || nameIdx === -1) {
    alert('CSV must have "tool_code" and "name" columns. Type column is optional (defaults to equipment).');
    return;
  }

  const existingCodes = new Set(data.tools.map(t => t.toolCode.toLowerCase()));
  csvRows = [];

  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',').map(c => c.trim().replace(/^["']|["']$/g, ''));
    const code = cols[codeIdx]?.trim();
    const name = cols[nameIdx]?.trim();
    let type = (cols[typeIdx] || '').trim().toLowerCase();
    if (type !== 'plant' && type !== 'equipment') type = 'equipment';

    if (!code || !name) continue;

    const isDuplicate = existingCodes.has(code.toLowerCase());
    existingCodes.add(code.toLowerCase()); // catch dupes within the CSV too

    csvRows.push({ toolCode: code, name, type, duplicate: isDuplicate });
  }

  if (csvRows.length === 0) {
    alert('No valid rows found in CSV.');
    return;
  }

  // Render preview
  const tbody = document.getElementById('csv-preview-tbody');
  const newCount = csvRows.filter(r => !r.duplicate).length;
  const dupeCount = csvRows.filter(r => r.duplicate).length;

  document.getElementById('csv-status').innerHTML =
    `<span style="color:var(--success)">${newCount} new</span>` +
    (dupeCount > 0 ? ` &middot; <span style="color:var(--plant-text)">${dupeCount} duplicate (skipped)</span>` : '');

  tbody.innerHTML = csvRows.map(r => `<tr${r.duplicate ? ' style="opacity:0.4"' : ''}>
    <td>${r.toolCode}</td>
    <td>${r.name}</td>
    <td><span class="badge badge-${r.type}">${r.type}</span></td>
    <td>${r.duplicate ? '<span style="color:var(--plant-text)">Duplicate</span>' : '<span style="color:var(--success)">New</span>'}</td>
  </tr>`).join('');

  document.getElementById('csv-preview-wrap').style.display = csvRows.length ? '' : 'none';
  document.getElementById('csv-import').disabled = newCount === 0;
  document.getElementById('csv-modal').classList.add('active');
}

document.getElementById('csv-import').addEventListener('click', async () => {
  const toImport = csvRows.filter(r => !r.duplicate).map(r => ({
    toolCode: r.toolCode,
    name: r.name,
    type: r.type,
  }));
  document.getElementById('csv-modal').classList.remove('active');
  if (toImport.length === 0) return;

  await saveData('addToolsBulk', { tools: toImport });
  csvRows = [];
});

document.getElementById('csv-cancel').addEventListener('click', () => {
  document.getElementById('csv-modal').classList.remove('active');
  csvRows = [];
});

// ── Polling for live updates ──
setInterval(loadData, 5000);

// ── Init ──
loadData();
