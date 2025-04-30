from langchain_tavily import TavilySearch
from langchain.tools import tool
import requests
import re

from typing import Optional, List

from backend.config.settings import settings
from backend.tools.vector_store import load_faiss_index
from langchain.schema import Document

web_search_tool = TavilySearch(
    max_results=3,
    topic="general"
    )

@tool
def web_search(query: str) -> list:
    """Search on the web for a given query."""
    results = web_search_tool.invoke(query)
    return results


#Functions to query the WB API

BASE_URL = settings.BASE_WB_URL

import requests

@tool(
    name_or_callable="query_data",
    description=(
        "Call the World Bank API to fetch data after identifying the relevant indicators from semantic search). ")
)
def query_data(
    datasetId: str,
    indicatorIds: str,
    countryCodes="KEN",
    years: Optional[int] = None,
    top=15,
    skip: Optional[int] = 0
):
    """
    Query the Prosperity Data360 API to fetch data for multiple economies and indicators.

    Parameters:
        datasetId (str): Required. The dataset identifier (e.g., "CEQ.CEQD").
        indicatorIds (list of str): List of indicator IDs to filter the data.
        countryCodes (list of str, optional): List of ISO3 country codes, default for KEN always.
        years (list or int, optional): One or multiple years to filter.
        top (int, optional): The number of items to select.
        skip (int, optional): The number of items to skip in the result.

    Note:
        - If any filter value includes special characters (like commas), make sure to escape them correctly 
          (e.g., "Beans\\, dry").
    Example:
            query_data(
            datasetId="YALE.EPI",
            indicatorIds=["YALE.EPI.USD", "CYALE.EPI.USD"],
            countryCodes=["KEN"],
            top=10,
            skip=0
        )
    
        It is important to note that every indicatorId is prefixed with the datasetId.
        for example, if the datasetId is "YALE.EPI", the indicatorId for "EPI" would be "YALE.EPI.EPI".
        Querying the API with "YALE.EPI" as the datasetId and an indicatorId with a different prefix will not yield results.

    Returns:
        dict: The JSON response from the API.

    Raises:
        Exception: If the API call fails (i.e., non-200 status code).
    """
    
    base_url = "https://datacatalogapi.worldbank.org/dexapps/efi/data"
    params = {"datasetId": datasetId,
            "countryCodes": countryCodes,
            "indicatorIds": indicatorIds,
            "years": years,
            "top": top,
            "skip": skip}
    
        
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API call failed with status {response.status_code}: {response.text}")

@tool(
    name_or_callable="semantic_search",
    description=(
        "Search our internal knowledge base of Kenyan entrepreneurship "
        "PDFs and World Bank indicator metadata. "
        "Use when the user needs domain-specific or qualitative information. "
        "Takes arguments: query (str), k (int, optional, default=5), "
        "source (str, optional: 'entrepreneurship_pdf'|'csv_row'|'indicator_meta'). "
        "Returns a JSON list of {{'content':..., <metadata>}} entries."
    )
)
def semantic_search(
    query: str,
    k : int = 5,
    source: Optional[str] = None
) -> List[dict]:
    """
    Search the combined FAISS index of PDFs and indicator metadata.
    - `query`: free‐text search.
    - `k`: number of results to return.
    - `source` (optional): filter by metadata.source, e.g.
        • "entrepreneurship_pdf" to retrieve documents and economic reports related to Kenya's economy and entreprenurial ecosystem.
        • "csv_row" to retrieve indicator metadata in order to better query the WB API.
      If omitted, searches across all documents.

    Returns a list of dicts: each with `content` and all metadata keys.
    """
    vs = load_faiss_index()
    if source:
        docs: List[Document] = vs.similarity_search(query, k=k, filter={"source": source})
    else:
        docs: List[Document] = vs.similarity_search(query, k=k)
    results = []
    for d in docs:
        entry = {"content": d.page_content}
        entry.update(d.metadata or {})
        results.append(entry)
    return results

_PAT_IND = re.compile(r"INDICATOR_ID:\s*([^\|]+)")
_PAT_DS  = re.compile(r"DATASET_ID:\s*([^\|]+)")

@tool(
    name_or_callable="wb_api_query_with_semantic_search",
    description=(
      "1) Use semantic_search over your indexed CSV rows to find the most relevant indicator"
      "and dataset. Do not specify the country in your query, as the API will default to Kenya. "
      "For example, you can ask: 'GDP indicators' instead of 'GDP indicators for Kenya'. "
      "2) Query our internal knowledge base for relevant indicators"
      "Args: query (str), dataset_id (str, optional), k (int, optional). "
      "Returns the multiple dataset IDs and indicator IDs"
    )
)
def wb_api_query_with_semantic_search(
    query: str,
    dataset_id: Optional[str] = None,
    k: int = 3
) -> dict:
    # 1) Pull CSV‐row hits from FAISS
    hits = semantic_search.func(query=query, k=k, source="csv_row")

    indicator_ids = []
    dataset_ids   = []

    for h in hits:
        text = h.get("content", "")
        m_ind = _PAT_IND.search(text)
        if m_ind:
            indicator_ids.append(m_ind.group(1).strip())
        m_ds = _PAT_DS.search(text)
        if m_ds:
            dataset_ids.append(m_ds.group(1).strip())

    # Dedupe
    indicator_ids = list(dict.fromkeys(indicator_ids))
    dataset_ids   = list(dict.fromkeys(dataset_ids))

    if not indicator_ids:
        raise Exception("No relevant indicator found in the Knowledge Base.")


    result = {
        "datasetId":dataset_ids,
        "indicatorIds":indicator_ids,
        "countryCodes":"KEN",
    }

    return result