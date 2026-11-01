import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, ToolMessage
from sqlalchemy import create_engine

# Project path and configuration must be available before importing application modules.
src_dir = Path(__file__).resolve().parent
project_root = src_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

from src.audit import write_audit_log  # noqa: E402
from src.orchestrator import agent, agent_model, load_system_prompt  # noqa: E402

logger = logging.getLogger(__name__)
admin_database_url = os.environ["DATABASE_URL"]
AGENT_FAILURE_MESSAGE = "The assistant could not complete that request. Please try again."


def extract_message_text(content: Any) -> str:
    """Extract displayable text from LangChain/OpenAI message content."""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = [
            str(item.get("text")) for item in content if isinstance(item, dict) and item.get("text")
        ]
        parts.extend(item for item in content if isinstance(item, str))
        return "\n".join(parts)

    return str(content)


def reset_conversation() -> None:
    """Start a UI and LangGraph conversation on a new thread."""

    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []


def thread_has_messages(thread_config: dict[str, Any]) -> bool:
    """Use the checkpoint as the source of truth for prompt initialization."""

    state = agent.get_state(thread_config)
    return bool(state.values.get("messages"))


@st.cache_resource
def get_admin_engine(database_url: str):
    return create_engine(database_url)


st.set_page_config(
    page_title="Cold-Chain Operations Assistant",
    page_icon="🧊",
    layout="wide",
)

st.title("🧊 Cold-Chain Operations Assistant")
st.caption(
    "Shipment telemetry, compliance guidance, weather analysis, and operational decision support."
)

st.session_state.setdefault("thread_id", str(uuid.uuid4()))
st.session_state.setdefault("messages", [])

thread_config = {"configurable": {"thread_id": st.session_state.thread_id}}

with st.sidebar:
    st.header("Control center")
    page = st.radio("View", ["Dispatch Console", "Audit Logs"])
    st.divider()
    st.caption(f"Model: `{agent_model}`")
    st.caption(f"Session: `{st.session_state.thread_id[:8]}...`")
    st.button(
        "New session",
        icon=":material/add_comment:",
        width="stretch",
        on_click=reset_conversation,
    )

if page == "Dispatch Console":
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            for trace in message.get("traces", []):
                with st.expander(trace["label"]):
                    if trace["type"] == "tool_call":
                        st.json(trace["content"])
                    else:
                        st.code(trace["content"], language="text")

    user_input = st.chat_input(
        "Ask about shipments, risks, weather, or SOP guidance...",
        submit_mode="disable",
    )
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        write_audit_log(
            session_id=st.session_state.thread_id,
            node_name="user_prompt",
            tool_name=None,
            content={"prompt": user_input},
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            traces: list[dict[str, Any]] = []
            final_response = ""
            status = st.status(":shimmer[Analyzing request]", expanded=True, type="compact")

            try:
                input_messages = [HumanMessage(content=user_input)]
                if not thread_has_messages(thread_config):
                    input_messages.insert(0, load_system_prompt())

                for event in agent.stream(
                    {"messages": input_messages},
                    config=thread_config,
                    stream_mode="updates",
                ):
                    for node_name, node_state in event.items():
                        if node_name == "reasoner":
                            latest_message = node_state["messages"][-1]
                            for tool_call in getattr(latest_message, "tool_calls", []):
                                tool_name = tool_call["name"]
                                tool_args = tool_call["args"]
                                status.write(f"Requested `{tool_name.replace('_', ' ')}`")
                                traces.append(
                                    {
                                        "type": "tool_call",
                                        "label": f"Tool input · {tool_name}",
                                        "content": tool_args,
                                    }
                                )
                                write_audit_log(
                                    session_id=st.session_state.thread_id,
                                    node_name="reasoner",
                                    tool_name=tool_name,
                                    content={"arguments": tool_args},
                                )

                            text_content = extract_message_text(latest_message.content)
                            if text_content and not getattr(latest_message, "tool_calls", []):
                                final_response = text_content

                        elif node_name == "tools":
                            for message in node_state.get("messages", []):
                                if not isinstance(message, ToolMessage):
                                    continue

                                tool_content = extract_message_text(message.content)
                                status.write(f"Received `{message.name.replace('_', ' ')}` result")
                                traces.append(
                                    {
                                        "type": "tool_result",
                                        "label": f"Tool result · {message.name}",
                                        "content": tool_content,
                                    }
                                )
                                write_audit_log(
                                    session_id=st.session_state.thread_id,
                                    node_name="tools",
                                    tool_name=message.name,
                                    content={"result": tool_content},
                                )

                status.update(label="Analysis complete", state="complete", expanded=False)

                if not final_response:
                    raise RuntimeError("Agent completed without a final response")

                st.markdown(final_response)
                write_audit_log(
                    session_id=st.session_state.thread_id,
                    node_name="reasoner_final",
                    tool_name=None,
                    content={"response": final_response},
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": final_response, "traces": traces}
                )

            except Exception as exc:
                logger.exception("Agent execution failed")
                status.update(label="Analysis unavailable", state="error", expanded=False)
                write_audit_log(
                    session_id=st.session_state.thread_id,
                    node_name="agent_error",
                    tool_name=None,
                    content={
                        "error_type": type(exc).__name__,
                        "details": str(exc),
                    },
                )
                st.error(AGENT_FAILURE_MESSAGE)
                st.session_state.messages.append(
                    {"role": "assistant", "content": AGENT_FAILURE_MESSAGE, "traces": traces}
                )

elif page == "Audit Logs":
    st.subheader("Agent audit trail")
    st.caption(
        "Execution history for local operators. This view uses the admin database connection."
    )

    try:
        query = """
            SELECT id, created_at, session_id, node_name, tool_name, content
            FROM agent_views.agent_audit_logs
            ORDER BY created_at DESC
            LIMIT 500
        """
        with get_admin_engine(admin_database_url).connect() as connection:
            audit_logs = pd.read_sql(query, connection)

        if audit_logs.empty:
            st.info("No audit events yet. Run a query in the Dispatch Console.")
        else:
            st.dataframe(
                audit_logs,
                hide_index=True,
                alt="Most recent agent audit events",
            )
    except Exception:
        logger.exception("Could not load audit logs")
        st.error("Audit logs are currently unavailable. Please try again later.")
