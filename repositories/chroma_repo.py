from typing import Optional
from chromadb.api.client import ClientAPI
import os
import chromadb
from core import config

_client: Optional[ClientAPI] = None

def get_chroma_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        chroma_path = os.path.join(config.DATA_DIR, "chroma_db")
        os.makedirs(chroma_path, exist_ok=True)
        _client = chromadb.PersistentClient(path=chroma_path)
    return _client

def get_or_create_collection(name: str):
    return get_chroma_client().get_or_create_collection(name=name)


def query_collection(
    collection_name: str,
    query_embedding: list[float],
    top_k: int = 5,
) -> dict:
    collection = get_or_create_collection(collection_name)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    return results
