import express from 'express';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import db from './db.js';
import toolsRouter from './routes/tools.js';
import projectsRouter from './routes/projects.js';
import movementsRouter from './routes/movements.js';
import { sseHandler } from './sse.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.PORT || 3001;

app.use(express.json());

// API routes
app.use('/api/tools', toolsRouter);
app.use('/api/projects', projectsRouter);
app.use('/api/movements', movementsRouter);

// SSE endpoint
app.get('/api/events', sseHandler);

// Dashboard stats
app.get('/api/stats', (req, res) => {
  const tools = db.prepare('SELECT current_location_type, COUNT(*) as count FROM tools GROUP BY current_location_type').all();
  const activeProjects = db.prepare("SELECT COUNT(*) as count FROM projects WHERE status = 'active'").get();
  const recentMovements = db.prepare(`
    SELECT m.*, t.name AS tool_name, t.tool_code,
           tp.name AS to_project_name
    FROM tool_movements m
    JOIN tools t ON m.tool_id = t.id
    LEFT JOIN projects tp ON m.to_project_id = tp.id
    ORDER BY m.moved_at DESC LIMIT 5
  `).all();

  const totalTools = tools.reduce((sum, r) => sum + r.count, 0);
  const warehouseTools = tools.find((r) => r.current_location_type === 'warehouse')?.count || 0;
  const assignedTools = tools.find((r) => r.current_location_type === 'project')?.count || 0;

  res.json({
    totalTools,
    warehouseTools,
    assignedTools,
    activeProjects: activeProjects.count,
    recentMovements,
  });
});

// In production, serve the built React app
if (process.env.NODE_ENV === 'production') {
  const distPath = join(__dirname, '..', 'dist');
  app.use(express.static(distPath));
  app.get('*', (req, res) => {
    res.sendFile(join(distPath, 'index.html'));
  });
}

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
