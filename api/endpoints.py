from fastapi import APIRouter, HTTPException
from domain.schemas import ScrapeRequest, ProcessRequest, DiscoverRequest, AskRequest
from services.rag_service import RAGService
from providers import discovery
from repositories import chroma_repo

router = APIRouter()
rag_service = RAGService()

@router.post("/collection/init")
def init_collection(collection_name: str = "wiki_rag"):
    try:
        count = rag_service.init_collection(collection_name)
        return {"status": "ok", "message": f"{collection_name} pronta para uso.", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape/discover")
def discover_pages(request: DiscoverRequest):
    try:
        pages = discovery.discover_all_pages(use_cache=request.use_cache)
        return {
            "status": "success",
            "count": len(pages),
            "pages": pages[:50], 
            "message": "Lista completa disponível no arquivo page_manifest.json"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape/extract")
def extract_page(request: ScrapeRequest):
    try:
        result = rag_service.process_and_index_url(request.url, request.collection_name)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process/embed")
def process_and_embed(request: ProcessRequest):
    try:
        result = rag_service.batch_process_local_chunks(request.collection_name, request.limit)
        return {
            "status": "completed",
            "processed": result["processed"],
            "total_files": result["total"],
            "errors": result["errors"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rag/documents")
def list_documents(collection_name: str = "wiki_rag", limit: int = 10, offset: int = 0):
    try:
        collection = chroma_repo.get_or_create_collection(collection_name)
        count = collection.count()
        results = collection.get(limit=limit, offset=offset)
        return {
            "total_count": count,
            "limit": limit,
            "offset": offset,
            "documents": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag/ask")
def ask_question(request: AskRequest):
    try:
        result = rag_service.ask(request.question, request.collection_name, request.top_k)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
