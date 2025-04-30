# backend/core/state.py
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class State(TypedDict):
    # every time a node emits a new message, add_messages will append it
    messages: Annotated[list, add_messages]
