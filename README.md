# Cold-Chain Logistics Assistant

A local Streamlit assistant for cold-chain dispatchers. It combines shipment telemetry, indexed SOP guidance, and current corridor weather through a small LangGraph ReAct workflow.

## Architecture

- **Streamlit UI** — chat-based dispatcher console and local operator audit view.
- **LangGraph** — a reasoner selects from explicitly defined tools, receives their results, and produces the final response.
- **PostgreSQL + pgvector** — read-only telemetry view, SOP embeddings, and append-only audit events.
- **Open-Meteo** — current weather for shipment coordinates.

The agent only reads approved telemetry views and SOP chunks. Audit events are written to `agent_views.agent_audit_logs` with insert-only permissions for `cold_chain_agent`.

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop
- An OpenAI API key

### Configure the environment

Copy `.env.example` to `.env` and set `OPENAI_API_KEY`. The default local database settings match `docker-compose.yaml`.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cold_chain
AGENT_DATABASE_URL=postgresql://cold_chain_agent:change-me@localhost:5432/cold_chain
OPENAI_API_KEY=your-key
```

### Start and prepare PostgreSQL

```bash
docker compose up -d
uv sync
```

Run the schema scripts in this order using the database owner connection:

```bash
psql "$DATABASE_URL" -f scripts/setup_sop_schema.sql
psql "$DATABASE_URL" -f scripts/setup_security_and_view.sql
psql "$DATABASE_URL" -f scripts/setup_audit_schema.sql
```

Then ingest the supplied telemetry and policy files:

```bash
uv run python scripts/ingest_legacy_data.py
uv run python scripts/ingest_sop.py
```

## Run the application

```bash
uv run streamlit run src/ui.py
```

For a terminal-only agent session:

```bash
uv run python src/orchestrator.py
```

## Request flow

1. A dispatcher submits a chat prompt.
2. The prompt is added to the append-only audit trail.
3. The LangGraph reasoner selects only the telemetry, SOP, or weather tools needed.
4. Tool requests and results are audit logged and presented in collapsed chat traces.
5. The reasoner returns an operational response, which is also audited.
6. Failures show a safe operator-facing message while diagnostic details remain in server and audit logs.

## Quality checks

```bash
uv run ruff check .
uv run ruff format --check src scripts tests
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q src scripts tests
```
