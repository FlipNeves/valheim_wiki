import os
import chromadb
from core import config

def verify():
    chroma_path = os.path.join(config.DATA_DIR, "chroma_db")
    print(f"Diretório do Chroma: {chroma_path}")
    
    os.makedirs(chroma_path, exist_ok=True)
    
    client = chromadb.PersistentClient(path=chroma_path)
    print("Conexão com o cliente estabelecida.")

    try:
        col = client.get_or_create_collection("verification_test")
        print("Acesso à coleção de teste confirmado.")
        
        count_before = col.count()
        col.upsert(
            ids=["test_id"],
            documents=["This is a test document to verify persistence."],
            metadatas=[{"source": "verification_script"}]
        )
        count_after = col.count()
        print(f"Contagem da coleção: {count_after} (era {count_before})")
        
        if count_after >= 1:
            print("Tudo certo: O ChromaDB está funcionando e persistindo os dados localmente!")
        else:
            print("Algo deu errado: O item não foi adicionado.")
            
    except Exception as e:
        print(f"Falha na verificação: {str(e)}")

if __name__ == "__main__":
    verify()
