import sys

from services.rag_service import RAGService
from repositories import chroma_repo


def main():
    collection_name = "wiki_rag"

    print("-" * 50)
    print("  Chatbot Valheim Wiki (RAG)")
    print("-" * 50)

    try:
        collection = chroma_repo.get_or_create_collection(collection_name)
        count = collection.count()
    except Exception as e:
        print(f"Erro ao conectar no ChromaDB: {e}")
        sys.exit(1)

    if count == 0:
        print(f"\nA coleção '{collection_name}' está vazia.")
        print("Rode primeiro: python pipeline.py --embed-only")
        sys.exit(1)

    print(f"Conectado! {count} chunks disponíveis na coleção '{collection_name}'.")
    print("Digite sua pergunta sobre Valheim (ou 'sair' para encerrar).\n")

    rag = RAGService()
    history: list[dict] = []

    while True:
        try:
            question = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAté mais!")
            break

        if not question:
            continue

        if question.lower() in ("sair", "exit", "quit"):
            print("Até mais!")
            break

        print("\nBuscando na wiki...\n")

        try:
            result = rag.ask(question, collection_name, history=history)

            answer = result["answer"]
            print(f"Bot: {answer}\n")

            # Acumula o histórico para preservar o contexto no próximo turno.
            # Usa a pergunta original (pt-BR) para que o histórico faça sentido
            # junto com as respostas em português.
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})

            print()

        except Exception as e:
            print(f"Erro ao processar a pergunta: {e}\n")


if __name__ == "__main__":
    main()
