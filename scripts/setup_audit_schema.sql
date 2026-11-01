CREATE SCHEMA IF NOT EXISTS agent_views;

CREATE TABLE IF NOT EXISTS agent_views.agent_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id TEXT NOT NULL,
    node_name TEXT NOT NULL,
    tool_name TEXT,
    content JSONB NOT NULL
);

REVOKE ALL ON agent_views.agent_audit_logs FROM cold_chain_agent;
GRANT INSERT ON agent_views.agent_audit_logs TO cold_chain_agent;

REVOKE ALL ON SEQUENCE agent_views.agent_audit_logs_id_seq FROM cold_chain_agent;
GRANT USAGE ON SEQUENCE agent_views.agent_audit_logs_id_seq TO cold_chain_agent;

GRANT USAGE ON SCHEMA agent_views TO cold_chain_agent;
