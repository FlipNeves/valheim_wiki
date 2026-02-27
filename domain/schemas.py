from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class WikiPageData(BaseModel):
    title: str
    url: str
    slug: str
    categories: List[str]
    infobox: Dict[str, Any]
    sections: List[Dict[str, Any]]
    full_text: str
    scraped_at: str

class RAGChunk(BaseModel):
    title: str
    url: str
    slug: str
    categories: List[str]
    content: str
    content_length: int
    scraped_at: str

class ScrapeRequest(BaseModel):
    url: str
    collection_name: str = "wiki_rag"

class ProcessRequest(BaseModel):
    collection_name: str = "wiki_rag"
    limit: Optional[int] = None

class DiscoverRequest(BaseModel):
    use_cache: bool = True

class AskRequest(BaseModel):
    question: str
    collection_name: str = "wiki_rag"
    top_k: int = 5

class SourceInfo(BaseModel):
    title: str
    url: str
    similarity: float

class AskResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    chunks_used: int
