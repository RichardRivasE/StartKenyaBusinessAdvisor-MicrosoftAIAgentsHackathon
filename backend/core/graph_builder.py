# backend/core/graph_builder.py
import threading
from typing import List

from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from backend.core.state import State
from backend.agents.rag_agent import rag_agent
from backend.tools.agent_tools import (
    web_search,
    semantic_search,
    wb_api_query_with_semantic_search,
    query_data
)
from .llm import llm
from langgraph.checkpoint.memory import MemorySaver

from langchain.globals import set_debug, set_verbose

# Set debug and verbose mode
#set_debug(True)
#set_verbose(True)

#define the graph
graph_builder = StateGraph(State)

#tools
tools = [web_search,
    semantic_search,
    wb_api_query_with_semantic_search,
    query_data
]

# memory
memory = MemorySaver()

graph_builder.add_node("rag_agent", rag_agent)


tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges("rag_agent", tools_condition)
graph_builder.add_edge("tools", "rag_agent")
graph_builder.set_entry_point("rag_agent")


graph = graph_builder.compile(checkpointer=memory)

config = {"configurable": {"thread_id": threading.get_ident()}}

def stream_graph_updates(user_input: str, 
                         config: dict = config, 
                         stream_mode: str = "values"):
    """
    Given raw user input, push it into the graph and print out the assistant replies.
    """
    init_state = {"messages": [{"role": "user", "content": user_input}]}
    for event in graph.stream(init_state, config):
        for node_output in event.values():
            # each node_output is a State; we grab the last message
            msg = node_output["messages"][-1]
            print(f"Assistant: {msg.content}")
