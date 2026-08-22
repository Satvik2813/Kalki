-- KALKI Supabase Schema Initialization
-- Requires the pgvector extension

CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Users
-- In Supabase, the user ID is a UUID. We reference auth.users for identity.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY REFERENCES auth.users ON DELETE CASCADE,
    email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Projects
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);

-- 3. Agent Runs (Mapping to AgentState)
CREATE TABLE IF NOT EXISTS agent_runs (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    objective TEXT NOT NULL,
    status TEXT NOT NULL,
    node TEXT NOT NULL,
    plan JSONB,
    current_task_id TEXT,
    plan_revisions INT NOT NULL DEFAULT 0,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_user ON agent_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_project ON agent_runs(project_id);

-- 4. Agent Events
CREATE TABLE IF NOT EXISTS agent_events (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    seq INT NOT NULL,
    message TEXT,
    data JSONB NOT NULL DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_agent_events_run ON agent_events(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_run_seq ON agent_events(run_id, seq);

-- 5. Memories (pgvector)
CREATE TABLE IF NOT EXISTS kalki_memories (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scope TEXT NOT NULL,
    content TEXT NOT NULL,
    project TEXT,
    session_id TEXT,
    tags JSONB NOT NULL DEFAULT '[]',
    metadata JSONB NOT NULL DEFAULT '{}',
    embedding VECTOR(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kalki_mem_scope ON kalki_memories(scope);
CREATE INDEX IF NOT EXISTS idx_kalki_mem_project ON kalki_memories(project);
CREATE INDEX IF NOT EXISTS idx_kalki_mem_user ON kalki_memories(user_id);

-- 6. User Integrations (GitHub, Vercel OAuth credentials)
CREATE TABLE IF NOT EXISTS user_integrations (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,              -- 'github' | 'vercel'
    account_id TEXT,
    account_username TEXT,
    encrypted_token TEXT NOT NULL,
    scopes JSONB NOT NULL DEFAULT '[]',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_provider UNIQUE (user_id, provider)
);
CREATE INDEX IF NOT EXISTS idx_user_integrations_user ON user_integrations(user_id);

-- 7. Local Projects (Pairing with local repository via KALKI CLI)
CREATE TABLE IF NOT EXISTS local_projects (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    local_path TEXT NOT NULL,
    git_remote TEXT,
    current_branch TEXT,
    status TEXT NOT NULL DEFAULT 'connected',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_local_projects_user ON local_projects(user_id);

-- 8. Unified KALKI Projects Context
CREATE TABLE IF NOT EXISTS kalki_projects (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    github_repo TEXT,
    vercel_project_id TEXT,
    local_path TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kalki_projects_user ON kalki_projects(user_id);

