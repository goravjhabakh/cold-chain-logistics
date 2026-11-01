# Setup
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sop_chunks (
    id BIGSERIAL PRIMARY KEY,
    source_file TEXT NOT NULL,
    file_format TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    file_hash TEXT NOT NULL,
    embedding VECTOR(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (source_file, chunk_index)
);

CREATE INDEX sop_chunks_embedding_hnsw_idx
ON sop_chunks
USING hnsw (embedding vector_cosine_ops);

# Verify
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'sop_chunks'
ORDER BY ordinal_position;

# Post ingestion
SELECT COUNT(*)
FROM sop_chunks;

SELECT
    id,
    source_file,
    chunk_index,
    LEFT(content, 120) AS content,
    metadata
FROM sop_chunks
ORDER BY source_file, chunk_index;

SELECT
    source_file,
    COUNT(*) AS chunk_count
FROM sop_chunks
GROUP BY source_file
ORDER BY source_file;

SELECT
    source_file,
    vector_dims(embedding) AS dimensions
FROM sop_chunks
LIMIT 10;

SELECT
    source_file,
    chunk_index,
    content
FROM sop_chunks
WHERE content ILIKE '%Tier 2%'
ORDER BY source_file, chunk_index;
