import { Router } from 'express';
import db from '../db.js';

const router = Router();

// List movements (most recent first)
router.get('/', (req, res) => {
  const movements = db.prepare(`
    SELECT
      m.*,
      t.name AS tool_name,
      t.tool_code,
      fp.name AS from_project_name,
      tp.name AS to_project_name
    FROM tool_movements m
    JOIN tools t ON m.tool_id = t.id
    LEFT JOIN projects fp ON m.from_project_id = fp.id
    LEFT JOIN projects tp ON m.to_project_id = tp.id
    ORDER BY m.moved_at DESC
    LIMIT 100
  `).all();

  res.json(movements);
});

export default router;
