import json
import os
from typing import Any

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

agent_database_url = os.environ["AGENT_DATABASE_URL"]

engine = create_engine(agent_database_url)


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

    if isinstance(content, str):
        payload = {"message": content}
    else:
        payload = content

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

    except Exception as exc:
        print(f"Audit logging failed: {exc}")


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
