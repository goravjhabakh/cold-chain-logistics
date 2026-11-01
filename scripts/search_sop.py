import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, text

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent

load_dotenv(project_root / ".env")

database_url = os.environ["DATABASE_URL"]
openai_api_key = os.environ["OPENAI_API_KEY"]

embedding_model_name = os.getenv(
    "EMBEDDING_MODEL",
    "text-embedding-3-small",
)

embedding_dimensions = 1536

openai_client = OpenAI(api_key=openai_api_key)
engine = create_engine(database_url)


def generate_query_embedding(query: str) -> list[float]:
    response = openai_client.embeddings.create(
        model=embedding_model_name,
        input=query,
        dimensions=embedding_dimensions,
        encoding_format="float",
    )

    return response.data[0].embedding


def search_sop(query: str, limit: int = 3) -> None:
    embedding = generate_query_embedding(query)

    vector = "[" + ",".join(map(str, embedding)) + "]"

    sql = text(
        """
        SELECT
            source_file,
            chunk_index,
            content,
            metadata,
            embedding <=> CAST(:embedding AS VECTOR) AS distance
        FROM sop_chunks
        ORDER BY embedding <=> CAST(:embedding AS VECTOR)
        LIMIT :limit
        """
    )

    with engine.connect() as connection:
        results = connection.execute(
            sql,
            {
                "embedding": vector,
                "limit": limit,
            },
        ).mappings()

        rows = list(results)

    print(f"\nQuery: {query}\n")

    if not rows:
        print("No matching SOP chunks found.")
        return

    for index, row in enumerate(rows, start=1):
        similarity = 1 - float(row["distance"])

        print(f"--- Result {index} ---")
        print(f"Source: {row['source_file']}")
        print(f"Chunk: {row['chunk_index']}")
        print(f"Similarity: {similarity:.4f}")
        print()
        print(row["content"])
        print()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('Usage: uv run python scripts/search_sop.py "your question"')

    query = " ".join(sys.argv[1:]).strip()

    if not query:
        raise SystemExit("Query cannot be empty.")

    search_sop(query)


if __name__ == "__main__":
    main()
