import { Router } from 'express';
import db from '../db.js';
import { broadcast } from '../sse.js';

const router = Router();

// List tools (optional ?location=warehouse|project filter)
router.get('/', (req, res) => {
  const { location } = req.query;
  let sql = `
    SELECT t.*, p.name AS project_name, p.project_code AS project_project_code
    FROM tools t
    LEFT JOIN projects p ON t.current_project_id = p.id
  `;
  const params = [];

  if (location) {
    sql += ' WHERE t.current_location_type = ?';
    params.push(location);
  }

  sql += ' ORDER BY t.created_at DESC';
  res.json(db.prepare(sql).all(...params));
});

// Get single tool
router.get('/:id', (req, res) => {
  const tool = db.prepare(`
    SELECT t.*, p.name AS project_name, p.project_code AS project_project_code
    FROM tools t
    LEFT JOIN projects p ON t.current_project_id = p.id
    WHERE t.id = ?
  `).get(req.params.id);

  if (!tool) return res.status(404).json({ error: 'Tool not found' });
  res.json(tool);
});

// Create tool
router.post('/', (req, res) => {
  const { tool_code, name, category } = req.body;
  if (!tool_code?.trim() || !name?.trim() || !category) {
    return res.status(400).json({ error: 'tool_code, name, and category are required' });
  }
  if (!['plant', 'equipment'].includes(category)) {
    return res.status(400).json({ error: 'category must be plant or equipment' });
  }

  try {
    const result = db.prepare(
      'INSERT INTO tools (tool_code, name, category) VALUES (?, ?, ?)'
    ).run(tool_code.trim(), name.trim(), category);

    const tool = db.prepare('SELECT * FROM tools WHERE id = ?').get(result.lastInsertRowid);
    broadcast('tools', { type: 'INSERT', record: tool });
    res.status(201).json(tool);
  } catch (err) {
    if (err.message.includes('UNIQUE')) {
      return res.status(409).json({ error: 'Tool code already exists' });
    }
    throw err;
  }
});

// Assign tool to project
router.post('/:id/assign', (req, res) => {
  const { project_id, moved_by, note } = req.body;
  if (!project_id) {
    return res.status(400).json({ error: 'project_id is required' });
  }

  const tool = db.prepare('SELECT * FROM tools WHERE id = ?').get(req.params.id);
  if (!tool) return res.status(404).json({ error: 'Tool not found' });
  if (tool.current_location_type === 'project') {
    return res.status(400).json({ error: 'Tool is already assigned to a project. Return it first.' });
  }

  const project = db.prepare('SELECT * FROM projects WHERE id = ?').get(project_id);
  if (!project) return res.status(404).json({ error: 'Project not found' });

  const assign = db.transaction(() => {
    db.prepare(`
      INSERT INTO tool_movements (tool_id, from_location_type, from_project_id, to_location_type, to_project_id, moved_by, note)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(tool.id, tool.current_location_type, tool.current_project_id, 'project', project_id, moved_by?.trim() || null, note?.trim() || null);

    db.prepare(`
      UPDATE tools SET current_location_type = 'project', current_project_id = ?, status = 'assigned', updated_at = datetime('now')
      WHERE id = ?
    `).run(project_id, tool.id);
  });

  assign();

  const updated = db.prepare('SELECT * FROM tools WHERE id = ?').get(tool.id);
  broadcast('tools', { type: 'UPDATE', record: updated });
  broadcast('movements', { type: 'INSERT' });
  res.json(updated);
});

// Return tool to warehouse
router.post('/:id/return', (req, res) => {
  const { moved_by, note } = req.body;

  const tool = db.prepare('SELECT * FROM tools WHERE id = ?').get(req.params.id);
  if (!tool) return res.status(404).json({ error: 'Tool not found' });
  if (tool.current_location_type === 'warehouse') {
    return res.status(400).json({ error: 'Tool is already in warehouse' });
  }

  const returnTool = db.transaction(() => {
    db.prepare(`
      INSERT INTO tool_movements (tool_id, from_location_type, from_project_id, to_location_type, to_project_id, moved_by, note)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).run(tool.id, tool.current_location_type, tool.current_project_id, 'warehouse', null, moved_by?.trim() || null, note?.trim() || null);

    db.prepare(`
      UPDATE tools SET current_location_type = 'warehouse', current_project_id = NULL, status = 'available', updated_at = datetime('now')
      WHERE id = ?
    `).run(tool.id);
  });

  returnTool();

  const updated = db.prepare('SELECT * FROM tools WHERE id = ?').get(tool.id);
  broadcast('tools', { type: 'UPDATE', record: updated });
  broadcast('movements', { type: 'INSERT' });
  res.json(updated);
});

export default router;
