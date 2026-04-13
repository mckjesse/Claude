import { Router } from 'express';
import db from '../db.js';

const router = Router();

// List projects with tool counts
router.get('/', (req, res) => {
  const projects = db.prepare(`
    SELECT p.*, COUNT(t.id) AS tool_count
    FROM projects p
    LEFT JOIN tools t ON t.current_project_id = p.id
    GROUP BY p.id
    ORDER BY p.created_at DESC
  `).all();

  res.json(projects);
});

// Get single project
router.get('/:id', (req, res) => {
  const project = db.prepare('SELECT * FROM projects WHERE id = ?').get(req.params.id);
  if (!project) return res.status(404).json({ error: 'Project not found' });
  res.json(project);
});

// Get tools assigned to a project
router.get('/:id/tools', (req, res) => {
  const tools = db.prepare(
    'SELECT * FROM tools WHERE current_project_id = ? ORDER BY name'
  ).all(req.params.id);
  res.json(tools);
});

// Create project
router.post('/', (req, res) => {
  const { project_code, name, site_address } = req.body;
  if (!project_code?.trim() || !name?.trim()) {
    return res.status(400).json({ error: 'project_code and name are required' });
  }

  try {
    const result = db.prepare(
      'INSERT INTO projects (project_code, name, site_address) VALUES (?, ?, ?)'
    ).run(project_code.trim(), name.trim(), site_address?.trim() || null);

    const project = db.prepare('SELECT * FROM projects WHERE id = ?').get(result.lastInsertRowid);
    res.status(201).json(project);
  } catch (err) {
    if (err.message.includes('UNIQUE')) {
      return res.status(409).json({ error: 'Project code already exists' });
    }
    throw err;
  }
});

export default router;
