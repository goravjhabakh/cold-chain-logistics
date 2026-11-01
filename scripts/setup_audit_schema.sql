CREATE TABLE agent_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id TEXT NOT NULL,
    node_name TEXT NOT NULL,
    tool_name TEXT,
    content JSONB NOT NULL
);

GRANT INSERT ON agent_audit_logs TO cold_chain_agent;

GRANT USAGE, SELECT
ON SEQUENCE agent_audit_logs_id_seq
TO cold_chain_agent;

REVOKE UPDATE, DELETE, TRUNCATE
ON agent_audit_logs
FROM cold_chain_agent;
