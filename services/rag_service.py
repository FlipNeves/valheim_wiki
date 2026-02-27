import os
import json
import glob
from typing import List, Dict, Optional, Any

from core import config, text_utils, exporter
from providers import wiki, ollama
from repositories import chroma_repo

class RAGService:
    def __init__(self):
        self.chroma_repo = chroma_repo

    def init_collection(self, collection_name: str):
        collection = self.chroma_repo.get_or_create_collection(collection_name)
        return collection.count()

    def process_and_index_url(self, url: str, collection_name: str) -> Dict[str, Any]:
        data = wiki.scrape_page(url)
        if not data:
            return {"status": "error", "message": f"Não foi possível ler a URL: {url}"}

        json_path, chunk_path = exporter.export_page(data)
        
        with open(chunk_path, "r", encoding="utf-8") as f:
            chunk_data = json.load(f)
            
        content = chunk_data.get("content", "")
        title = chunk_data.get("title", "")
        
        if not content:
            return {"status": "warning", "message": f"A página '{title}' parece estar vazia."}

        text_chunks = text_utils.split_text_into_chunks(content, title=title)
        
        self._index_chunks(text_chunks, chunk_data, collection_name)
        
        return {
            "status": "success",
            "message": f"Página '{title}' processada e dividida em {len(text_chunks)} partes.",
            "json_path": json_path,
            "chunk_path": chunk_path
        }

    def batch_process_local_chunks(self, collection_name: str, limit: Optional[int] = None) -> Dict[str, Any]:
        chunk_files = glob.glob(os.path.join(config.RAG_CHUNKS_DIR, "*.json"))
        if limit:
            chunk_files = chunk_files[:limit]
            
        processed_count = 0
        errors = []
        
        for file_path in chunk_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                content = data.get("content", "")
                if not content: continue
                
                text_chunks = text_utils.split_text_into_chunks(content, title=data.get("title", ""))
                self._index_chunks(text_chunks, data, collection_name)
                processed_count += 1
                
            except Exception as e:
                errors.append(f"Error processing {file_path}: {str(e)}")
        
        return {
            "processed": processed_count,
            "total": len(chunk_files),
            "errors": errors
        }

    def _index_chunks(self, text_chunks: List[str], base_data: Dict[str, Any], collection_name: str):
        collection = self.chroma_repo.get_or_create_collection(collection_name)
        title = base_data.get("title", "")
        
        ids, embeddings, documents, metadatas = [], [], [], []
        
        base_meta = {k: v for k, v in base_data.items() if k != "content" and isinstance(v, (str, int, float, bool))}
        if "categories" in base_data and isinstance(base_data["categories"], list):
            base_meta["categories"] = ", ".join(base_data["categories"])
        
        for i, chunk_text in enumerate(text_chunks):
            chunk_id = f"{ollama.generate_deterministic_id(chunk_text, title)}_{i}"
            embedding = ollama.generate_embedding(chunk_text)
            
            meta = base_meta.copy()
            meta["chunk_index"] = i
            meta["total_chunks"] = len(text_chunks)
            
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk_text)
            metadatas.append(meta)
        
        collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)

    def ask(
        self,
        question: str,
        collection_name: str = "wiki_rag",
        top_k: int = 5,
        min_similarity: float = 0.0,
        translate: bool = True,
        history: Optional[list] = None,
    ) -> dict:
        # Traduz a pergunta para inglês antes de gerar o embedding,
        # pois os chunks da wiki foram indexados em inglês.
        if translate:
            question_en = ollama.translate_text(question, target_lang="en")
        else:
            question_en = question

        query_embedding = ollama.generate_embedding(question_en)

        results = chroma_repo.query_collection(collection_name, query_embedding, top_k)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        chunks = []
        filtered_out = []

        for meta, dist, doc in zip(metadatas, distances, documents):
            similarity = round(1 / (1 + dist), 4)
            entry = {
                "title": meta.get("title", ""),
                "url": meta.get("url", ""),
                "similarity": similarity,
                "chunk_index": meta.get("chunk_index"),
                "content": doc,
            }
            if similarity >= min_similarity:
                chunks.append(entry)
            else:
                filtered_out.append(entry)

        answer = ollama.chat_with_context(question, chunks, history=history)

        return {
            "answer": answer,
            "question": question,
            "chunks_used": len(chunks),
            "chunks": chunks,
            "filtered_out": filtered_out,
            "sources": [
                {"title": c["title"], "url": c["url"], "similarity": c["similarity"]}
                for c in chunks
            ]
        }

