# backend/agents/rag_agent.py

from backend.core.llm import llm
from backend.core.llm import summarizer
from backend.core.state import State
from langchain_core.messages.function import FunctionMessage

# import every tool you bound in llm.py
from backend.tools.agent_tools import (
    web_search,
    semantic_search,
    wb_api_query_with_semantic_search,
    query_data
)

FUNCTIONS = {
    "web_search": web_search,
    "semantic_search": semantic_search,
    "wb_api_query_with_semantic_search":wb_api_query_with_semantic_search,
    "query_data": query_data,
}

TOOL_SYSTEM_PROMPT = [
    {
        "role": "system",
        "content": """
You are a business advisor for young entrepreneurs in Kenya. You have access to four tools:
1) semantic_search – search internal PDFs for domain-specific insight regarding Kenya's entreprenurial landscape;
2) wb_api_query_with_semantic_search – search for relevant indicators from the World Bank API to identify the right parameters for the user’s query;
3) query_data – search for specific data points in the World Bank API using the indicator ID and dataset ID from the previous tool.
4) web_search  – fall-back internet search for general knowledge.

When answering, prefer internal data (semantic_search or query_data).
Please note that when you perform the search for indicators, do not specify the country, as the API will default to Kenya.
"""
    }
]

SUMMARIZE_THRESHOLD = 20
SUMMARIZE_CHUNK     = 10

def _summarize_history(history: list) -> str:
    """Ask the LLM to condense old messages into 3 bullet points (no tools!)."""
    # 1) Pull only pure user/assistant turns into simple dicts
    pure = []
    for m in history:
        role    = getattr(m, "role", None)
        name    = getattr(m, "name", None)
        content = getattr(m, "content", None)
        if (role == "user" or (role == "assistant" and name is None)) and content:
            pure.append({"role": role, "content": content})

    # 2) Build a clean summary prompt
    prompt = [
        {
            "role": "system",
            "content": "Summarize the following conversation in 3 bullet points (no tools!):"
        }
    ] + pure

    # 3) Invoke the unbound summarizer with function calling disabled
    summary_response = summarizer.invoke(prompt, function_call=None)
    return summary_response.content

def rag_agent(state: State) -> State:
    # 1) Summarize old history if needed
    history = state["messages"]
    if len(history) > SUMMARIZE_THRESHOLD:
        old  = history[:SUMMARIZE_CHUNK]
        rest = history[SUMMARIZE_CHUNK:]
        summary_text = _summarize_history(old)
        memory = {
            "role": "system",
            "content": f"Conversation so far (summary):\n{summary_text}"
        }
        history = [memory] + rest


    filtered = [m for m in history if getattr(m,"role",None) != "tool"]

    msgs = TOOL_SYSTEM_PROMPT + filtered
    response = llm.invoke(msgs)

    if isinstance(response, FunctionMessage):
        tool_name = response.name
        tool_args = response.arguments
        tool_call_id = response.tool_calls[0].id

        print(f"\n🔧 Function call detected: {response.name}, args={response.arguments!r}\n")
        tool_output = FUNCTIONS[tool_name](**tool_args)

        msgs += [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "arguments": tool_args
                }
            ]
        },

        {
            "role": "function",
            "name": tool_name,
            "tool_call_id": tool_call_id,
            "content": tool_output
        }
        ]

        response = llm.invoke(msgs)

    return {"messages": [response]}
