import os
from pathlib import Path

from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent

load_dotenv(project_root / ".env")


def require_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required configuration: {name}")

    return value


DATABASE_URL = require_env("DATABASE_URL")
AGENT_DATABASE_URL = require_env("AGENT_DATABASE_URL")
OPENAI_API_KEY = require_env("OPENAI_API_KEY")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "text-embedding-3-small",
)

AGENT_MODEL = os.getenv(
    "AGENT_MODEL",
    "gpt-6-luna",
)
