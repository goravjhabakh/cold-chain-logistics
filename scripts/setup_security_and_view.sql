-- ============================================================
-- AI AGENT DATABASE SECURITY + SEMANTIC VIEW
-- ============================================================

-- 1. Dedicated schema for agent-facing views
CREATE SCHEMA IF NOT EXISTS agent_views;


-- 2. Clean semantic view over raw shipment telemetry
CREATE OR REPLACE VIEW agent_views.active_shipments AS
SELECT
    "TS_UTC" AS timestamp,
    "V_LAT" AS latitude,
    "V_LON" AS longitude,
    "IOT_TEMP_VAL_C"::DOUBLE PRECISION AS current_temperature_c,
    "CGO_COND_CD" AS cargo_condition,
    "RISK_CLS_TXT" AS risk_classification,
    "DELAY_PROB_DEC" AS delay_probability,
    "PRT_CNG_LVL" AS port_congestion_level,
    "RT_RSK_IDX" AS route_risk_index
FROM shipment_telemetry_raw;


-- 3. Create dedicated login role for the AI agent
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_roles
        WHERE rolname = 'cold_chain_agent'
    ) THEN
        CREATE ROLE cold_chain_agent
            LOGIN
            PASSWORD 'cold_chain_agent';
    END IF;
END
$$;


-- 4. Remove broad/default access
REVOKE ALL ON shipment_telemetry_raw FROM cold_chain_agent;
REVOKE ALL ON SCHEMA public FROM cold_chain_agent;


-- 5. Allow the agent to access only the semantic schema
GRANT USAGE ON SCHEMA agent_views TO cold_chain_agent;
GRANT SELECT ON agent_views.active_shipments TO cold_chain_agent;


-- 6. Allow SOP retrieval
GRANT SELECT ON sop_chunks TO cold_chain_agent;


-- 7. Make the intended restrictions explicit
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON shipment_telemetry_raw
FROM cold_chain_agent;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
ON sop_chunks
FROM cold_chain_agent;
