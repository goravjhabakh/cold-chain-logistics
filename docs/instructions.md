# Cold Chain Logistics AI Assistant

This document describes how to run the current local project from scratch.

## 1. Prerequisites

- Python managed with `uv`
- Docker / Docker Compose
- PostgreSQL client or VS Code database extension
- OpenAI API key

## 2. Install dependencies

```bash
uv sync
```

## 3. Configure environment variables

Create `.env` in the project root:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cold_chain
AGENT_DATABASE_URL=postgresql+psycopg://cold_chain_agent:<agent-password>@localhost:5432/cold_chain

OPENAI_API_KEY=<your-key>
EMBEDDING_MODEL=text-embedding-3-small
AGENT_MODEL=gpt-6-luna
```

`DATABASE_URL` is used by setup and ingestion scripts.

`AGENT_DATABASE_URL` is used by the AI runtime and must point to the restricted `cold_chain_agent` role.

## 4. Start PostgreSQL + pgvector

```bash
docker compose up -d
docker compose ps
```

## 5. Ingest shipment telemetry

Dataset:

```text
https://www.kaggle.com/datasets/datasetengineer/logistics-and-supply-chain-dataset
```

Expected CSV:

```text
data/raw/dynamic_supply_chain_logistics_dataset.csv
```

Run:

```bash
uv run python scripts/ingest_legacy_data.py
```

Expected:

```text
Legacy ingestion complete: 32065 rows loaded.
```

Raw table:

```text
shipment_telemetry_raw
```

## 6. Create the SOP vector schema

Run:

```text
scripts/setup_sop_schema.sql
```

This enables pgvector and creates `sop_chunks` using 1536-dimensional embeddings.

## 7. Ingest SOP documents

Policy documents live in:

```text
data/policy/
```

Run:

```bash
uv run python scripts/ingest_sop.py
```

Test retrieval:

```bash
uv run python scripts/search_sop.py "What temperature counts as a cold-chain breach?"
```

## 8. Configure agent database security

Run:

```text
scripts/setup_security_and_view.sql
```

This creates:

```text
agent_views.active_shipments
```

and the restricted PostgreSQL role:

```text
cold_chain_agent
```

The agent can read approved operational data and SOP chunks, but cannot modify shipment data or access the raw telemetry table directly.

## 9. Configure audit logging

Run:

```text
scripts/setup_audit_schema.sql
```

Canonical audit table:

```text
agent_views.agent_audit_logs
```

The agent role has append-only access to this table.

## 10. Test the agent tools

```bash
uv run python src/agent_tools.py
```

Current tools:

- `find_shipments_near`
- `get_high_risk_shipments`
- `get_temperature_breaches`
- `search_compliance_sop`
- `fetch_corridor_conditions`

Telemetry tools use fixed parameterized SQL rather than arbitrary LLM-generated SQL.

## 11. Test the LangGraph agent

```bash
uv run python -m src.orchestrator
```

Example:

```text
Find shipments near Los Angeles around latitude 33.8 and longitude -118.1.
Check whether any violate the SOP for fresh perishables, check the weather,
and recommend what the dispatcher should do.
```

## 12. Run the Streamlit application

```bash
uv run streamlit run src/ui.py
```

The UI provides:

- dispatcher chat;
- progressively disclosed tool traces;
- session-based LangGraph state;
- controlled error handling;
- local/operator audit-log inspection.

## 13. Code quality

```bash
uv run ruff check .
uv run ruff format .
```

Run the project tests before deployment.

## Current status

Completed locally:

- structured telemetry ingestion;
- SOP RAG ingestion and semantic search;
- least-privilege database access;
- purpose-built agent tools;
- LangGraph orchestration;
- append-only audit logging;
- Streamlit UI.

Deployment is the next phase.
