import logging
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from src.agent_tools import (
    fetch_corridor_conditions,
    find_shipments_near,
    get_high_risk_shipments,
    get_temperature_breaches,
    search_compliance_sop,
)
from src.config import AGENT_MODEL

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

logger = logging.getLogger(__name__)

src_dir = Path(__file__).resolve().parent
project_root = src_dir.parent

prompt_path = src_dir / "prompts" / "system_prompt.txt"


# ---------------------------------------------------------
# Agent state
# ---------------------------------------------------------


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------------------------------
# LLM + tools
# ---------------------------------------------------------

tools = [
    find_shipments_near,
    get_high_risk_shipments,
    get_temperature_breaches,
    search_compliance_sop,
    fetch_corridor_conditions,
]

llm = ChatOpenAI(
    model=AGENT_MODEL,
)

llm_with_tools = llm.bind_tools(tools)


# ---------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------


def reasoning_node(state: AgentState) -> AgentState:
    response = llm_with_tools.invoke(state["messages"])

    return {
        "messages": [response],
    }


def handle_tool_error(error: Exception) -> str:
    """Keep unexpected tool errors recoverable without exposing diagnostics to users."""

    logger.error("Unexpected tool execution error", exc_info=error)
    return "The requested operational data could not be retrieved. Please try again."


# ---------------------------------------------------------
# Graph
# ---------------------------------------------------------

graph_builder = StateGraph(AgentState)

graph_builder.add_node(
    "reasoner",
    reasoning_node,
)

graph_builder.add_node(
    "tools",
    ToolNode(tools, handle_tool_errors=handle_tool_error),
)

graph_builder.add_edge(
    START,
    "reasoner",
)

graph_builder.add_conditional_edges(
    "reasoner",
    tools_condition,
)

graph_builder.add_edge(
    "tools",
    "reasoner",
)

agent = graph_builder.compile(
    checkpointer=MemorySaver(),
)


# ---------------------------------------------------------
# Prompt
# ---------------------------------------------------------


def load_system_prompt() -> SystemMessage:
    if not prompt_path.exists():
        raise FileNotFoundError(f"System prompt not found: {prompt_path}")

    content = prompt_path.read_text(encoding="utf-8").strip()

    return SystemMessage(
        content=content,
    )


# ---------------------------------------------------------
# Local CLI
# ---------------------------------------------------------


def main() -> None:
    system_prompt = load_system_prompt()

    config = {
        "configurable": {
            "thread_id": "local-development",
        }
    }

    first_turn = True

    print(f"Cold-chain agent ready (model: {AGENT_MODEL})")

    print("Type 'exit' or 'quit' to stop.")

    while True:
        user_input = input("\nDispatcher > ").strip()

        if not user_input:
            continue

        if user_input.lower() in {
            "exit",
            "quit",
        }:
            break

        messages: list[BaseMessage | tuple[str, str]] = [("user", user_input)]

        if first_turn:
            messages.insert(
                0,
                system_prompt,
            )
            first_turn = False

        events = agent.stream(
            {
                "messages": messages,
            },
            config=config,
            stream_mode="updates",
        )

        for event in events:
            for node_name, node_state in event.items():
                if node_name == "tools":
                    print("  [tools] Fetching required data...")

                if node_name == "reasoner":
                    latest_message = node_state["messages"][-1]

                    if latest_message.content:
                        print(f"\nAgent:\n{latest_message.content}")


if __name__ == "__main__":
    main()
