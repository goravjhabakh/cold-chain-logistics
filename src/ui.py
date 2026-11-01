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

# ---------------------------------------------------------
# Project path setup
# ---------------------------------------------------------

src_dir = Path(__file__).resolve().parent
project_root = src_dir.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

from src.audit import write_audit_log  # noqa: E402
from src.orchestrator import agent, agent_model, load_system_prompt  # noqa: E402

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

src_dir = Path(__file__).resolve().parent
project_root = src_dir.parent

load_dotenv(project_root / ".env")

admin_database_url = os.environ["DATABASE_URL"]


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def extract_message_text(content: Any) -> str:
    """Extract displayable text from LangChain/OpenAI message content."""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)

            elif isinstance(item, dict):
                text = item.get("text")

                if text:
                    parts.append(str(text))

        return "\n".join(parts)

    return str(content)


# ---------------------------------------------------------
# Streamlit page
# ---------------------------------------------------------

st.set_page_config(
    page_title="Cold-Chain Operations Assistant",
    page_icon="🧊",
    layout="wide",
)

st.title("🧊 Cold-Chain Operations Assistant")
st.caption(
    "Shipment telemetry, compliance guidance, weather analysis, and operational decision support."
)


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_initialized" not in st.session_state:
    st.session_state.agent_initialized = False


thread_config = {
    "configurable": {
        "thread_id": st.session_state.thread_id,
    }
}


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:
    st.header("Control Center")

    page = st.radio(
        "View",
        [
            "Dispatch Console",
            "Audit Logs",
        ],
    )

    st.divider()

    st.caption(f"Model: `{agent_model}`")
    st.caption(f"Session: `{st.session_state.thread_id[:8]}...`")

    if st.button(
        "New Session",
        use_container_width=True,
    ):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.agent_initialized = False

        st.rerun()


# ---------------------------------------------------------
# Dispatch Console
# ---------------------------------------------------------

if page == "Dispatch Console":
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            for trace in message.get("traces", []):
                if trace["type"] == "tool_call":
                    with st.expander(f"Tool call: {trace['name']}"):
                        st.json(trace["args"])

                elif trace["type"] == "tool_result":
                    with st.expander(f"Tool result: {trace['name']}"):
                        st.code(
                            trace["content"],
                            language="text",
                        )

    if user_input := st.chat_input("Ask about shipments, risks, weather, or SOP guidance..."):
        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            traces = []
            final_response = ""

            input_messages = [
                HumanMessage(content=user_input),
            ]

            # Add the system prompt only once per LangGraph thread.
            if not st.session_state.agent_initialized:
                input_messages.insert(
                    0,
                    load_system_prompt(),
                )

                st.session_state.agent_initialized = True

            with st.status(
                "Analyzing request...",
                expanded=True,
            ) as status:
                events = agent.stream(
                    {
                        "messages": input_messages,
                    },
                    config=thread_config,
                    stream_mode="updates",
                )

                for event in events:
                    for node_name, node_state in event.items():
                        if node_name == "reasoner":
                            latest_message = node_state["messages"][-1]

                            # ---------------------------------
                            # Tool calls chosen by the LLM
                            # ---------------------------------

                            tool_calls = getattr(
                                latest_message,
                                "tool_calls",
                                [],
                            )

                            for tool_call in tool_calls:
                                tool_name = tool_call["name"]
                                tool_args = tool_call["args"]

                                status.update(label=(f"Using {tool_name}..."))

                                with st.expander(f"Tool call: {tool_name}"):
                                    st.json(tool_args)

                                traces.append(
                                    {
                                        "type": "tool_call",
                                        "name": tool_name,
                                        "args": tool_args,
                                    }
                                )

                                write_audit_log(
                                    session_id=(st.session_state.thread_id),
                                    node_name="reasoner",
                                    tool_name=tool_name,
                                    content={
                                        "arguments": tool_args,
                                    },
                                )

                            # ---------------------------------
                            # Final LLM response
                            # ---------------------------------

                            text_content = extract_message_text(latest_message.content)

                            if text_content:
                                final_response = text_content

                        # -------------------------------------
                        # Tool execution results
                        # -------------------------------------

                        elif node_name == "tools":
                            status.update(label="Retrieving operational data...")

                            for message in node_state.get(
                                "messages",
                                [],
                            ):
                                if not isinstance(
                                    message,
                                    ToolMessage,
                                ):
                                    continue

                                tool_content = extract_message_text(message.content)

                                with st.expander(f"Tool result: {message.name}"):
                                    st.code(
                                        tool_content,
                                        language="text",
                                    )

                                traces.append(
                                    {
                                        "type": "tool_result",
                                        "name": message.name,
                                        "content": tool_content,
                                    }
                                )

                                write_audit_log(
                                    session_id=(st.session_state.thread_id),
                                    node_name="tools",
                                    tool_name=message.name,
                                    content={
                                        "result": tool_content,
                                    },
                                )

                status.update(
                    label="Analysis complete",
                    state="complete",
                    expanded=False,
                )

            if final_response:
                st.markdown(final_response)

                write_audit_log(
                    session_id=st.session_state.thread_id,
                    node_name="reasoner_final",
                    tool_name=None,
                    content={
                        "response": final_response,
                    },
                )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": final_response,
                        "traces": traces,
                    }
                )

            else:
                st.error("The agent completed without producing a final response.")


# ---------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------

elif page == "Audit Logs":
    st.subheader("Agent Audit Trail")

    st.caption(
        "Execution history recorded by the agent. This view uses the admin database connection."
    )

    try:
        admin_engine = create_engine(admin_database_url)

        query = """
            SELECT
                id,
                created_at,
                session_id,
                node_name,
                tool_name,
                content
            FROM agent_views.agent_audit_logs
            ORDER BY created_at DESC
            LIMIT 500
        """

        with admin_engine.connect() as connection:
            audit_logs = pd.read_sql(
                query,
                connection,
            )

        if audit_logs.empty:
            st.info("No audit events yet. Run a query in the Dispatch Console.")
        else:
            st.dataframe(
                audit_logs,
                hide_index=True,
                use_container_width=True,
            )

    except Exception as exc:
        st.error(f"Could not load audit logs: {exc}")
