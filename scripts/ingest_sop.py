import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pypdf
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
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

policy_dir = project_root / "data" / "policy"

supported_extensions = {".md", ".txt", ".pdf", ".csv", ".xlsx"}

chunk_size = 600
chunk_overlap = 60

# ---------------------------------------------------------
# Database + OpenAI
# ---------------------------------------------------------

print(f"Using embedding model: {embedding_model_name}")

openai_client = OpenAI(api_key=openai_api_key)
engine = create_engine(database_url)

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def calculate_file_hash(file_path: Path) -> str:
    """Return a SHA-256 hash for detecting document changes."""

    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def parse_document(file_path: Path) -> list[Document]:
    """Parse and chunk one supported policy document."""

    extension = file_path.suffix.lower()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    if extension == ".md":
        raw_text = file_path.read_text(encoding="utf-8")

        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "header_1"),
                ("##", "header_2"),
                ("###", "header_3"),
            ]
        )

        header_documents = markdown_splitter.split_text(raw_text)

        return splitter.split_documents(header_documents)

    if extension == ".txt":
        raw_text = file_path.read_text(encoding="utf-8")

        return splitter.split_documents([Document(page_content=raw_text)])

    if extension == ".pdf":
        documents: list[Document] = []

        with file_path.open("rb") as file:
            reader = pypdf.PdfReader(file)

            for page_number, page in enumerate(reader.pages, start=1):
                content = page.extract_text()

                if not content or not content.strip():
                    continue

                documents.append(
                    Document(
                        page_content=content,
                        metadata={"page_number": page_number},
                    )
                )

        return splitter.split_documents(documents)

    if extension in {".csv", ".xlsx"}:
        if extension == ".csv":
            dataframe = pd.read_csv(file_path)
        else:
            dataframe = pd.read_excel(file_path)

        documents = []

        for row_index, row in dataframe.iterrows():
            values = [
                f"{column}: {value}"
                for column, value in row.items()
                if pd.notna(value) and str(value).strip()
            ]

            if not values:
                continue

            documents.append(
                Document(
                    page_content=" | ".join(values),
                    metadata={"row_index": int(row_index)},
                )
            )

        return documents

    raise ValueError(f"Unsupported file type: {extension}")


def get_existing_documents() -> dict[str, str]:
    """Return source_file -> file_hash currently stored in PostgreSQL."""

    query = text(
        """
        SELECT source_file, MAX(file_hash) AS file_hash
        FROM sop_chunks
        GROUP BY source_file
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(query)

        return {row.source_file: row.file_hash for row in rows}


def delete_document(source_file: str) -> None:
    """Delete all chunks belonging to a source document."""

    query = text(
        """
        DELETE FROM sop_chunks
        WHERE source_file = :source_file
        """
    )

    with engine.begin() as connection:
        connection.execute(
            query,
            {"source_file": source_file},
        )


def generate_embeddings(contents: list[str]) -> list[list[float]]:
    """Generate OpenAI embeddings for a batch of text chunks."""

    response = openai_client.embeddings.create(
        model=embedding_model_name,
        input=contents,
        dimensions=embedding_dimensions,
        encoding_format="float",
    )

    return [item.embedding for item in response.data]


def insert_chunks(
    file_path: Path,
    file_hash: str,
    chunks: list[Document],
) -> None:
    """Generate embeddings and insert document chunks."""

    valid_chunks = [chunk for chunk in chunks if chunk.page_content.strip()]

    contents = [chunk.page_content.strip() for chunk in valid_chunks]

    if not contents:
        return

    print(f"  Generating embeddings for {len(contents)} chunk(s)...")

    embeddings = generate_embeddings(contents)

    query = text(
        """
        INSERT INTO sop_chunks (
            source_file,
            file_format,
            chunk_index,
            content,
            metadata,
            file_hash,
            embedding
        )
        VALUES (
            :source_file,
            :file_format,
            :chunk_index,
            :content,
            CAST(:metadata AS JSONB),
            :file_hash,
            CAST(:embedding AS VECTOR)
        )
        """
    )

    rows = []

    for chunk_index, (chunk, embedding) in enumerate(zip(valid_chunks, embeddings, strict=True)):
        rows.append(
            {
                "source_file": file_path.name,
                "file_format": file_path.suffix.removeprefix(".").upper(),
                "chunk_index": chunk_index,
                "content": chunk.page_content.strip(),
                "metadata": json.dumps(chunk.metadata),
                "file_hash": file_hash,
                "embedding": "[" + ",".join(map(str, embedding)) + "]",
            }
        )

    with engine.begin() as connection:
        connection.execute(query, rows)


# ---------------------------------------------------------
# Ingestion
# ---------------------------------------------------------


def main() -> None:
    if not policy_dir.exists():
        raise FileNotFoundError(f"Policy directory does not exist: {policy_dir}")

    policy_files = {
        path.name: path
        for path in policy_dir.iterdir()
        if path.is_file() and path.suffix.lower() in supported_extensions
    }

    print(f"Found {len(policy_files)} policy file(s).")

    existing_documents = get_existing_documents()

    # Remove documents that no longer exist locally.
    deleted_files = set(existing_documents) - set(policy_files)

    for file_name in deleted_files:
        print(f"Deleting removed document: {file_name}")
        delete_document(file_name)

    # Process new or modified documents.
    for file_name, file_path in policy_files.items():
        file_hash = calculate_file_hash(file_path)

        if existing_documents.get(file_name) == file_hash:
            print(f"Skipped unchanged file: {file_name}")
            continue

        print(f"Processing: {file_name}")

        chunks = parse_document(file_path)

        chunks = [chunk for chunk in chunks if chunk.page_content.strip()]

        if not chunks:
            print("  No valid content found.")
            continue

        # Replace old chunks only when the document changed.
        delete_document(file_name)

        insert_chunks(
            file_path=file_path,
            file_hash=file_hash,
            chunks=chunks,
        )

        print(f"  Inserted {len(chunks)} chunk(s).")

    print("SOP ingestion complete.")


if __name__ == "__main__":
    main()
