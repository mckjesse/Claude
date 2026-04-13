import initSqlJs from 'sql.js';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { mkdirSync, readFileSync, writeFileSync, existsSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const dbPath = join(__dirname, '..', 'data', 'inventory.db');
mkdirSync(join(__dirname, '..', 'data'), { recursive: true });

// Initialize sql.js and load/create the database
const SQL = await initSqlJs();
let sqlDb;

if (existsSync(dbPath)) {
  const buffer = readFileSync(dbPath);
  sqlDb = new SQL.Database(buffer);
} else {
  sqlDb = new SQL.Database();
}

// Persist to disk
function save() {
  const data = sqlDb.export();
  writeFileSync(dbPath, Buffer.from(data));
}

// Track whether we're inside a transaction (skip per-statement saves)
let inTransaction = false;

// Wrapper that matches better-sqlite3 API used by routes:
//   db.prepare(sql).all(...params)  -> array of objects
//   db.prepare(sql).get(...params)  -> single object or undefined
//   db.prepare(sql).run(...params)  -> { lastInsertRowid, changes }
//   db.transaction(fn)              -> wrapped fn with BEGIN/COMMIT
//   db.exec(sql)                    -> run DDL

const db = {
  prepare(sql) {
    return {
      all(...params) {
        const stmt = sqlDb.prepare(sql);
        if (params.length) stmt.bind(params);
        const results = [];
        while (stmt.step()) {
          results.push(stmt.getAsObject());
        }
        stmt.free();
        return results;
      },

      get(...params) {
        const stmt = sqlDb.prepare(sql);
        if (params.length) stmt.bind(params);
        let result = undefined;
        if (stmt.step()) {
          result = stmt.getAsObject();
        }
        stmt.free();
        return result;
      },

      run(...params) {
        sqlDb.run(sql, params);
        const lastInsertRowid = sqlDb.exec('SELECT last_insert_rowid() as id')[0]?.values[0][0];
        const changes = sqlDb.getRowsModified();
        if (!inTransaction) save();
        return { lastInsertRowid, changes };
      },
    };
  },

  exec(sql) {
    sqlDb.run(sql);
    save();
  },

  transaction(fn) {
    return (...args) => {
      sqlDb.run('BEGIN');
      inTransaction = true;
      try {
        fn(...args);
        sqlDb.run('COMMIT');
        inTransaction = false;
        save();
      } catch (err) {
        inTransaction = false;
        try { sqlDb.run('ROLLBACK'); } catch (_) { /* already rolled back */ }
        throw err;
      }
    };
  },
};

// Enable foreign keys
sqlDb.run('PRAGMA foreign_keys = ON');

// Create tables (one at a time — sql.js doesn't support multi-statement exec)
sqlDb.run(`
  CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    site_address TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'on_hold')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  )
`);

sqlDb.run(`
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
  )
`);

sqlDb.run(`
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
  )
`);

sqlDb.run('CREATE INDEX IF NOT EXISTS idx_tools_current_project ON tools(current_project_id)');
sqlDb.run('CREATE INDEX IF NOT EXISTS idx_tools_location ON tools(current_location_type)');
sqlDb.run('CREATE INDEX IF NOT EXISTS idx_tool_movements_tool ON tool_movements(tool_id)');
sqlDb.run('CREATE INDEX IF NOT EXISTS idx_tool_movements_moved_at ON tool_movements(moved_at DESC)');

save();

export default db;
