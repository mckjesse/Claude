-- Tool Inventory Tracker - Database Schema
-- Run this in Supabase SQL Editor to set up the database

-- Projects table
create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  project_code text not null unique,
  name text not null,
  site_address text,
  status text not null default 'active' check (status in ('active', 'completed', 'on_hold')),
  created_at timestamptz not null default now()
);

-- Tools table
create table if not exists tools (
  id uuid primary key default gen_random_uuid(),
  tool_code text not null unique,
  name text not null,
  category text not null check (category in ('plant', 'equipment')),
  status text not null default 'available' check (status in ('available', 'assigned', 'out_of_service')),
  current_location_type text not null default 'warehouse' check (current_location_type in ('warehouse', 'project')),
  current_project_id uuid references projects(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Tool movements history
create table if not exists tool_movements (
  id uuid primary key default gen_random_uuid(),
  tool_id uuid not null references tools(id) on delete cascade,
  from_location_type text not null,
  from_project_id uuid references projects(id) on delete set null,
  to_location_type text not null,
  to_project_id uuid references projects(id) on delete set null,
  moved_by text,
  note text,
  moved_at timestamptz not null default now()
);

-- Indexes for common queries
create index if not exists idx_tools_current_project on tools(current_project_id);
create index if not exists idx_tools_status on tools(status);
create index if not exists idx_tools_location on tools(current_location_type);
create index if not exists idx_tool_movements_tool on tool_movements(tool_id);
create index if not exists idx_tool_movements_moved_at on tool_movements(moved_at desc);

-- Auto-update updated_at on tools
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger tools_updated_at
  before update on tools
  for each row execute function update_updated_at();

-- Enable realtime for tools and tool_movements
alter publication supabase_realtime add table tools;
alter publication supabase_realtime add table tool_movements;

-- Disable RLS for V1 (no auth)
alter table projects enable row level security;
alter table tools enable row level security;
alter table tool_movements enable row level security;

-- Allow all access via anon key (no auth in V1)
create policy "Allow all on projects" on projects for all using (true) with check (true);
create policy "Allow all on tools" on tools for all using (true) with check (true);
create policy "Allow all on tool_movements" on tool_movements for all using (true) with check (true);
