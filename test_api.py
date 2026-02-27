import requests
import time
import subprocess
import os
from core.config import RAG_CHUNKS_DIR

BASE_URL = "http://localhost:8000"

def wait_for_api():
    print("Aguardando a API subir...")
    for _ in range(10):
        try:
            requests.get(f"{BASE_URL}/docs")
            print("API disponível.")
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    print("Não foi possível conectar à API.")
    return False

def test_collection_init():
    print("\nTestando inicialização da coleção...")
    response = requests.post(f"{BASE_URL}/collection/init")
    if response.status_code == 200:
        print("Coleção configurada:", response.json())
        return True
    else:
        print("Erro ao configurar coleção:", response.text)
        return False

def test_discover():
    print("\nTestando descoberta de páginas (Cache)...")
    manifest_path = os.path.join(os.getcwd(), "data", "page_manifest.json")
    if not os.path.exists(manifest_path):
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, "w") as f:
            f.write('[{"title": "Test Page", "url": "http://example.com/wiki/Test", "slug": "Test"}]')

    try:
        response = requests.post(f"{BASE_URL}/scrape/discover", json={"use_cache": True})
        if response.status_code == 200:
            print("Descoberta funcionando:", response.json())
            return True
        else:
            print("Erro na descoberta:", response.text)
            return False
    except Exception as e:
        print(f"❌ Exceção na descoberta: {e}")
        return False

def test_process_embed():
    print("\nTestando processamento de embeddings...")
    if not os.path.exists(RAG_CHUNKS_DIR) or not os.listdir(RAG_CHUNKS_DIR):
        print("Criando arquivo de teste em rag_chunks...")
        os.makedirs(RAG_CHUNKS_DIR, exist_ok=True)
        with open(os.path.join(RAG_CHUNKS_DIR, "test_chunk.json"), "w", encoding="utf-8") as f:
            f.write('{"title": "Test Title", "slug": "test_slug", "content": "This is a test content.", "categories": ["Test"]}')
    
    response = requests.post(f"{BASE_URL}/process/embed", json={"collection_name": "wiki_rag_test", "limit": 1})
    if response.status_code == 200:
        print("Processamento finalizado:", response.json())
        return True
    else:
        print("Erro no processamento:", response.text)
        return False

def test_list_documents():
    print("\nVerificando listagem de documentos...")
    try:
        response = requests.get(f"{BASE_URL}/rag/documents", params={"collection_name": "wiki_rag_test", "limit": 5})
        if response.status_code == 200:
            data = response.json()
            print(f"Documentos recuperados: {len(data['documents']['ids'])} itens.")
            return True
        else:
            print("Erro ao listar documentos:", response.text)
            return False
    except Exception as e:
        print(f"❌ Exceção ao listar: {e}")
        return False

if __name__ == "__main__":
    print("Subindo o servidor da API...")
    process = subprocess.Popen(["uvicorn", "api.main:app", "--port", "8000"])
    
    try:
        if wait_for_api():
            test_collection_init()
            test_discover()
            test_process_embed()
            test_list_documents()
    finally:
        print("\nDesligando a API...")
        process.terminate()
