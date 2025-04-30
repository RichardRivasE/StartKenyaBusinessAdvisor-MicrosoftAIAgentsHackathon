# backend/main.py
from core.graph_builder import stream_graph_updates
import threading


def main():
    
    print("Type ‘exit’ to quit.")
    while True:
        prompt = input("You: ")
        if prompt.lower() in ("exit", "quit", "q"):
            break
        stream_graph_updates(prompt)

if __name__ == "__main__":
    main()
