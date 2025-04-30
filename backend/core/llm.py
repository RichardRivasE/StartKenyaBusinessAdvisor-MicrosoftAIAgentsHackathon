
import langchain_openai
from backend.config.settings import settings
from backend.tools.agent_tools import (
    web_search, 
    query_data,
    semantic_search,
    wb_api_query_with_semantic_search,
    query_data
)


llm = langchain_openai.ChatOpenAI(
    model="openai/gpt-4o-mini",
    api_key=settings.GITHUB_TOKEN,                   
    base_url="https://models.github.ai/inference",
    temperature=0.0,
    max_completion_tokens=4000,
)

summarizer = langchain_openai.ChatOpenAI(
    model="openai/gpt-4o-mini",
    api_key=settings.GITHUB_TOKEN,                   
    base_url="https://models.github.ai/inference",
    temperature=0.0,
    max_completion_tokens=4000,
    functions=None)

tools = [
    web_search,
    query_data,
    semantic_search,
    wb_api_query_with_semantic_search,
]


llm = llm.bind_tools(tools)
