# Cold Chain Logistics Project

## Ingesting Data

- Download the dataset from:
  `https://www.kaggle.com/datasets/datasetengineer/logistics-and-supply-chain-dataset`

- Initialize the Python project with `uv`:

```bash
uv init
```

- Add the required dependencies:

```bash
uv add pandas sqlalchemy "psycopg[binary]" python-dotenv
uv add --dev ruff
```

- Create `.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cold_chain
```

- Run PostgreSQL + pgvector locally with Docker:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: cold-chain-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: cold_chain
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Start the database:

```bash
docker compose up -d
```

- Run the legacy data ingestion script:

```bash
uv run python scripts/ingest_legacy_data.py
```

Expected result:

```text
Legacy ingestion complete: 32065 rows loaded.
```

The data is stored in:

```text
shipment_telemetry_raw
```
