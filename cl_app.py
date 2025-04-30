import threading
import chainlit as cl
from backend.core.graph_builder import graph
from langchain_core.messages.function import FunctionMessage

config = {"configurable": {"thread_id": threading.get_ident()}}

@cl.on_message
async def main(message: cl.Message):
    # 1) Extract plain user text
    user_text = message.content

    init_state = {"messages":[{"role":"user","content":user_text}]}
    for event in graph.stream(init_state, config=config):
        for node_output in event.values():
            # Grab the last message in this node's state
            m = node_output["messages"][-1]

            msg = m.model_dump()  
            role    = msg.get("role", "assistant")
            content = msg.get("content") or ""
            name    = msg.get("name")

            if role == "assistant" and name is None and content != "":
                await cl.Message(content=content).send()