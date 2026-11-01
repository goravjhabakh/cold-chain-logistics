# Phase 0 — Ingest Legacy Fleet Data

## Goal

Take the provided CSV dataset and load it into a local PostgreSQL database.

For now, think of PostgreSQL as the client's **legacy operational database**.

Architecture:

```text
CSV dataset
    ↓
Python ingestion script
    ↓
PostgreSQL + pgvector
    ↓
Fleet / shipment tables
```

---

## 1. Start PostgreSQL + pgvector

We will run PostgreSQL locally using Docker.

Create a `docker-compose.yml` in the project root:

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

Start it:

```bash
docker compose up -d
```

Check that it is running:

```bash
docker ps
```

You should see:

```text
cold-chain-postgres
```

---

## 2. Enable pgvector

Connect to the database.

You can use:

- VS Code PostgreSQL extension
- DBeaver
- pgAdmin
- `psql`

Connection:

```text
Host: localhost
Port: 5432
Database: cold_chain
Username: postgres
Password: postgres
```

Then run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Check:

```sql
SELECT extname
FROM pg_extension
WHERE extname = 'vector';
```

You should get:

```text
vector
```

Phase 0 does not actually need vectors yet, but enabling it now keeps the database ready for Phase 1.

---

## 3. Set Up Python

Create a virtual environment:

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the project's dependencies:

```powershell
pip install -r requirements.txt
```

If the project still contains MSSQL-specific dependencies such as `pyodbc`, we will eventually replace those with PostgreSQL equivalents.

The main PostgreSQL Python driver should be:

```bash
pip install psycopg[binary]
```

You may also use SQLAlchemy if the project already uses it.

---

## 4. Configure the Database Connection

Create/update `.env`:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/cold_chain
```

Do not hardcode the connection string throughout the Python code.

Your application should read `DATABASE_URL`.

Conceptually:

```text
Python
  ↓
DATABASE_URL
  ↓
PostgreSQL
```

This will also make migration to Neon later easy.

---

## 5. Update the Legacy Data Ingestion Script

The original project uses:

```text
scripts/ingest_legacy_data.py
```

Its job stays the same:

```text
CSV
 ↓
read rows
 ↓
clean / normalize if needed
 ↓
insert into PostgreSQL
```

What changes is only the database connection.

Instead of connecting to MSSQL, it should connect to:

```text
localhost:5432
cold_chain
```

Do not redesign the entire dataset yet.

For Phase 0, preserve the original dataset structure as much as practical because we're pretending this is legacy client data.

For example, if the original table was:

```text
TBL_SC_FLEET_HIST_RAW
```

you could keep a similar name:

```sql
CREATE TABLE tbl_sc_fleet_hist_raw (
    ...
);
```

The important part is:

> raw legacy data stays raw.

We will make cleaner views on top of it later.

---

## 6. Run the Ingestion

Run:

```powershell
python scripts\ingest_legacy_data.py
```

The script should:

1. Read your CSV.
2. Create the required table if necessary.
3. Insert the data.
4. Report how many rows were inserted.

---

## 7. Verify the Data

Connect to PostgreSQL and run:

```sql
SELECT COUNT(*)
FROM tbl_sc_fleet_hist_raw;
```

Then inspect a few rows:

```sql
SELECT *
FROM tbl_sc_fleet_hist_raw
LIMIT 10;
```

You want to confirm:

- rows were loaded
- columns look correct
- timestamps look correct
- latitude/longitude are numeric
- temperature values are numeric
- shipment identifiers are present

Don't worry about making everything beautiful yet.

This is the **raw legacy layer**.

---

## Phase 0 Complete When

You should have:

```text
Docker
└── PostgreSQL + pgvector
      └── cold_chain database
            └── tbl_sc_fleet_hist_raw
                    └── CSV data
```

And this works:

```sql
SELECT COUNT(*)
FROM tbl_sc_fleet_hist_raw;
```

---

# Phase 1 — SOP Ingestion with pgvector

## Goal

Take the cold-chain SOP documents and make them searchable by the AI agent.

The original project uses Pinecone.

We will instead use:

```text
PostgreSQL
+
pgvector
```

Architecture:

```text
SOP documents
      ↓
text extraction
      ↓
chunking
      ↓
embedding model
      ↓
PostgreSQL + pgvector
      ↓
semantic search
```

---

## 1. Understand What We're Building

Assume an SOP contains something like:

```text
Fresh produce must remain between 2°C and 8°C.

A Tier 1 escalation should be created when...
```

The AI shouldn't read every SOP file every time someone asks a question.

Instead we split the documents into smaller pieces:

```text
Chunk 1
"Fresh produce must remain between 2°C and 8°C."

Chunk 2
"A Tier 1 escalation should be created when..."

Chunk 3
...
```

Each chunk gets converted into an embedding:

```text
text
 ↓
embedding model
 ↓
[0.143, -0.82, 0.42, ...]
```

We store both in PostgreSQL.

---

## 2. Create the SOP Table

For a lightweight local embedding model such as `all-MiniLM-L6-v2`, embeddings contain **384 dimensions**.

Create:

```sql
CREATE TABLE sop_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_name TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    embedding VECTOR(384)
);
```

Now PostgreSQL can store:

```text
document name
chunk number
actual SOP text
metadata
vector embedding
```

---

## 3. Install Embedding Dependencies

For a completely free local setup:

```bash
pip install sentence-transformers
```

We can use:

```text
sentence-transformers/all-MiniLM-L6-v2
```

This model is small enough that you do **not need a GPU server**.

CPU is fine for this dataset.

Important distinction:

```text
sentence-transformers → creates embeddings

pgvector → stores/searches embeddings
```

pgvector itself does not create them.

---

## 4. Replace the Pinecone Ingestion Script

The original project has something like:

```text
scripts/ingest_sop_pinecone.py
```

For our version, I'd rename it to:

```text
scripts/ingest_sop.py
```

Its responsibilities:

```text
1. Read SOP files
2. Extract text
3. Split text into chunks
4. Generate embeddings
5. Insert chunks + embeddings into PostgreSQL
```

Conceptually:

```python
SOP document

→ "Fresh produce should..."
→ "Tier 1 escalation..."
→ "Driver must contact..."

→ embedding model

→ PostgreSQL
```

---

## 5. Chunk the SOP Documents

Start simple.

Something around:

```text
500-800 characters per chunk
```

with a small overlap:

```text
50-100 characters
```

You do not need complicated RAG frameworks yet.

Avoid jumping straight into LangChain/LlamaIndex unless the project actually needs them.

Understanding the basic pipeline first is more useful.

---

## 6. Generate the Embeddings

Conceptually:

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

embedding = model.encode(
    "Fresh produce must remain between 2°C and 8°C."
)
```

That produces:

```text
384 numbers
```

Store those numbers in:

```text
sop_chunks.embedding
```

---

## 7. Run SOP Ingestion

Eventually the command should simply be:

```powershell
python scripts\ingest_sop.py
```

The script should output something like:

```text
Found 3 SOP documents
Generated 87 chunks
Generated embeddings
Inserted 87 chunks into PostgreSQL
```

---

## 8. Verify the SOP Data

Check:

```sql
SELECT COUNT(*)
FROM sop_chunks;
```

Then:

```sql
SELECT
    document_name,
    chunk_index,
    LEFT(content, 100)
FROM sop_chunks
LIMIT 10;
```

You should see actual SOP content.

---

## 9. Test Semantic Search

Generate an embedding for a question such as:

```text
What temperature should fresh produce be kept at?
```

Then query:

```sql
SELECT
    document_name,
    content,
    embedding <=> %s::vector AS distance
FROM sop_chunks
ORDER BY embedding <=> %s::vector
LIMIT 5;
```

`<=>` performs cosine-distance search.

The top results should contain SOP sections related to cargo temperature.

That proves the RAG retrieval layer works.

---

## 10. Add a Vector Index

For a small dataset, brute-force search is already fine.

But to learn how production vector search works, add an HNSW index:

```sql
CREATE INDEX sop_chunks_embedding_idx
ON sop_chunks
USING hnsw (embedding vector_cosine_ops);
```

Don't obsess over tuning this yet.

Our SOP dataset will probably be tiny.

---

# Phase 1 Complete When

Your database should now look roughly like:

```text
PostgreSQL + pgvector
│
├── tbl_sc_fleet_hist_raw
│      └── operational / shipment data
│
└── sop_chunks
       ├── SOP text
       ├── metadata
       └── embeddings
```

And both of these should work:

```sql
SELECT COUNT(*)
FROM tbl_sc_fleet_hist_raw;
```

and:

```sql
SELECT COUNT(*)
FROM sop_chunks;
```

More importantly, a semantic search such as:

```text
"What are the temperature limits for fresh cargo?"
```

should return the relevant SOP chunks.

---

# Where We Are After Phase 1

At this point we have built the two data sources the future AI agent needs:

```text
                         PostgreSQL + pgvector
                        /                     \
                       /                       \
            Fleet / shipment data           SOP knowledge
                    ↓                             ↓
               SQL queries                 Vector search
                       \                       /
                        \                     /
                          Future AI Agent
```

We have **not built the agent yet**.

That comes later.

For now:

**Phase 0 = structured operational data**

**Phase 1 = unstructured company knowledge / RAG**
