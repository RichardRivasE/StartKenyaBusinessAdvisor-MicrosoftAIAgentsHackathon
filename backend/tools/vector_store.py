# backend/tools/vector_store_builder.py

import os
import time
import pandas as pd
from typing import List

from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
# from core.llm import embeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document
import langchain_openai

from backend.config.settings import settings


embeddings_client = langchain_openai.OpenAIEmbeddings(
    model="text-embedding-3-large",
    api_key=settings.GITHUB_TOKEN,
    base_url="https://models.inference.ai.azure.com"
)

# ───────────── CONFIG ─────────────
PDF_CHUNK_SIZE    = 2000      # ≈300–400 tokens per chunk
PDF_CHUNK_OVERLAP = 400

CSV_BATCH_SIZE    = 55       # rows per embedding call
SECONDS_PER_CALL  = 60 / 14   # to keep under 15 calls/min

PERSIST_DIR       = "data/vectorstore"
# ───────────────────────────────────

def _pdf_chunks(pdf_paths: List[str]):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=PDF_CHUNK_SIZE,
        chunk_overlap=PDF_CHUNK_OVERLAP,
    )
    for path in pdf_paths:
        for doc in PyPDFLoader(path).load():
            for chunk in splitter.split_documents([doc]):
                yield Document(
                    page_content=chunk.page_content,
                    metadata={
                        "source": "entrepreneurship_pdf",
                        "path": os.path.basename(path),
                    },
                )

def _csv_chunks(csv_path: str):
    df = pd.read_csv(csv_path)
    # pick whichever columns you want to pre-format
    df = df[['INDICATOR_ID','INDICATOR_NAME','DATASET_ID','DATASET_TITLE','DATASET_DESCRIPTION','label_1']]
    df = df[df['label_1'] != 'Other']
    texts = [
        f"INDICATOR_ID: {r.INDICATOR_ID} | NAME: {r.INDICATOR_NAME} | "
        f"DATASET_ID: {r.DATASET_ID} | TITLE: {r.DATASET_TITLE} | "
        f"DESCRIPTION: {r.DATASET_DESCRIPTION} | TOPIC: {r.label_1}"
        for r in df.itertuples()
    ]
    for i in range(0, len(texts), CSV_BATCH_SIZE):
        for idx, txt in enumerate(texts[i:i+CSV_BATCH_SIZE]):
            yield Document(
                page_content=txt,
                metadata={"source": "csv_row", "row_index": i + idx},
            )

def build_faiss_index(
    pdf_paths: List[str],
    csv_path: str,
    persist_dir: str = PERSIST_DIR
):
    """
    Build a new FAISS index from scratch by:
      1) taking your first batch to create the index
      2) adding remaining docs in batches
    """
    os.makedirs(persist_dir, exist_ok=True)

    docs = list(_pdf_chunks(pdf_paths)) + list(_csv_chunks(csv_path))
    if not docs:
        raise ValueError("No documents found to index.")

    first_batch = docs[:CSV_BATCH_SIZE]

    vs = FAISS.from_documents(first_batch, embeddings_client)

    for i in range(CSV_BATCH_SIZE, len(docs), CSV_BATCH_SIZE):
        batch = docs[i : i + CSV_BATCH_SIZE]
        vs.add_documents(batch)
        time.sleep(SECONDS_PER_CALL)

    vs.save_local(persist_dir)
    return vs

def load_faiss_index(persist_dir: str = PERSIST_DIR) -> FAISS:
    """
    Load your pre-built FAISS index—no embedding calls here.
    """

    return FAISS.load_local(persist_dir, 
                            embeddings_client,
                            allow_dangerous_deserialization=True)

def add_new_documents(
    vs: FAISS,
    new_pdf_paths: List[str] = None,
    new_csv_path: str = None,
):
    """
    Incrementally embed & add new docs—then call vs.save_local() again.
    """
    to_add = []
    if new_pdf_paths:
        to_add.extend(_pdf_chunks(new_pdf_paths))
    if new_csv_path:
        to_add.extend(_csv_chunks(new_csv_path))

    # batch-add them exactly like above
    for i in range(0, len(to_add), CSV_BATCH_SIZE):
        vs.add_documents(to_add[i : i + CSV_BATCH_SIZE])
        time.sleep(SECONDS_PER_CALL)

    return vs
