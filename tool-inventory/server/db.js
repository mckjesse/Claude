import Database from 'better-sqlite3';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dbPath = join(__dirname, '..', 'data', 'inventory.db');

// Ensure data directory exists
import { mkdirSync } from 'fs';
mkdirSync(join(__dirname, '..', 'data'), { recursive: true });

const db = new Database(dbPath);

// Performance pragmas
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

// Create tables
db.exec(`
  CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    site_address TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'on_hold')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('plant', 'equipment')),
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'assigned', 'out_of_service')),
    current_location_type TEXT NOT NULL DEFAULT 'warehouse' CHECK (current_location_type IN ('warehouse', 'project')),
    current_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS tool_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id INTEGER NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    from_location_type TEXT NOT NULL,
    from_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    to_location_type TEXT NOT NULL,
    to_project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    moved_by TEXT,
    note TEXT,
    moved_at TEXT NOT NULL DEFAULT (datetime('now'))
  );

  CREATE INDEX IF NOT EXISTS idx_tools_current_project ON tools(current_project_id);
  CREATE INDEX IF NOT EXISTS idx_tools_location ON tools(current_location_type);
  CREATE INDEX IF NOT EXISTS idx_tool_movements_tool ON tool_movements(tool_id);
  CREATE INDEX IF NOT EXISTS idx_tool_movements_moved_at ON tool_movements(moved_at DESC);
`);

export default db;
