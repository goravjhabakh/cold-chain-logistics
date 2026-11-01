import json
import logging
from typing import Any

from sqlalchemy import create_engine, text

from src.config import AGENT_DATABASE_URL

logger = logging.getLogger(__name__)

engine = create_engine(AGENT_DATABASE_URL)


def build_audit_payload(content: Any) -> Any:
    """Normalize text audit content without changing structured payloads."""

    return {"message": content} if isinstance(content, str) else content


def write_audit_log(
    session_id: str,
    node_name: str,
    tool_name: str | None,
    content: Any,
) -> None:
    """
    Append an agent execution event to the audit log.

    Audit failures are intentionally non-fatal so logging problems
    do not break the dispatcher workflow.
    """

    payload = build_audit_payload(content)

    query = text(
        """
        INSERT INTO agent_views.agent_audit_logs (
            session_id,
            node_name,
            tool_name,
            content
        )
        VALUES (
            :session_id,
            :node_name,
            :tool_name,
            CAST(:content AS JSONB)
        )
        """
    )

    try:
        with engine.begin() as connection:
            connection.execute(
                query,
                {
                    "session_id": session_id,
                    "node_name": node_name,
                    "tool_name": tool_name,
                    "content": json.dumps(payload, default=str),
                },
            )

    except Exception:
        logger.exception("Audit logging failed")


if __name__ == "__main__":
    write_audit_log(
        session_id="audit-test",
        node_name="test",
        tool_name="manual_test",
        content={
            "status": "working",
        },
    )

    print("Audit test complete.")
