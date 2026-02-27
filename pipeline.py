import argparse
import json
import os
import sys
import time
import logging
from datetime import datetime, timezone

from core import config, exporter, text_utils
from providers import discovery, wiki, ollama
from repositories import chroma_repo

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


def _setup_logging():
    config.ensure_dirs()
    logging.basicConfig(
        filename=config.ERROR_LOG_PATH,
        level=logging.ERROR,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )


def _load_progress() -> dict:
    if os.path.exists(config.PROGRESS_PATH):
        with open(config.PROGRESS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_urls": [], "last_run": None}


def _save_progress(progress: dict):
    progress["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(config.PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def phase_discover(args) -> list[dict]:
    print("\n" + "-" * 40)
    print("Mapeando as páginas da wiki...")
    print("-" * 40)

    start = time.time()
    pages = discovery.discover_all_pages(use_cache=False)
    elapsed = time.time() - start

    print(f"\nBusca finalizada. Levou {elapsed:.1f}s.")
    print(f"Encontrei {len(pages)} páginas únicas.")
    return pages


def phase_scrape(args, pages: list[dict]) -> list[dict]:
    print("\n" + "-" * 40)
    print("Iniciando a extração do conteúdo...")
    print("-" * 40)

    if args.category:
        cat_lower = args.category.lower()
        pages = [p for p in pages if cat_lower in p.get("slug", "").lower()
                 or cat_lower in p.get("title", "").lower()]
        print(f"Filtrando apenas por '{args.category}': {len(pages)} itens.")

    if args.limit:
        pages = pages[:args.limit]
        print(f"Limitando o processamento a {args.limit} páginas.")

    progress = _load_progress()
    completed = set(progress["completed_urls"])
    pending = [p for p in pages if p["url"] not in completed]

    if len(pending) < len(pages):
        print(f"Retomando: {len(pages) - len(pending)} já prontas, faltam {len(pending)}.")

    if not pending:
        print("Tudo certo, todas as páginas já foram processadas!")
        return _load_existing_results()

    scraper = wiki._create_scraper()
    results = []
    errors = 0

    iterator = tqdm(pending, desc="Scraping", unit="pg") if HAS_TQDM else pending

    for i, page_info in enumerate(iterator):
        url = page_info["url"]
        title = page_info.get("title", url)

        if not HAS_TQDM:
            print(f"  [{i+1}/{len(pending)}] {title}...")

        try:
            data = wiki.scrape_page(url, scraper)
            if data:
                results.append(data)
                completed.add(url)

                if len(results) % 10 == 0:
                    progress["completed_urls"] = list(completed)
                    _save_progress(progress)
            else:
                errors += 1
                logging.error(f"Scraping retornou None: {url}")

        except Exception as e:
            errors += 1
            logging.error(f"Erro no scraping de {url}: {e}")

        if i < len(pending) - 1:
            wiki._delay()

    progress["completed_urls"] = list(completed)
    _save_progress(progress)

    print(f"\nExtração finalizada: {len(results)} sucessos e {errors} falhas.")
    return results


def phase_export(args, results: list[dict]):
    print("\n" + "-" * 40)
    print("Preparando arquivos para o RAG...")
    print("-" * 40)

    if not results:
        results = _load_existing_results()

    if not results:
        print("Não achei nada para exportar.")
        return

    exported = 0
    iterator = tqdm(results, desc="Exportando", unit="pg") if HAS_TQDM else results

    for i, page_data in enumerate(iterator):
        try:
            json_path, chunk_path = exporter.export_page(page_data)
            exported += 1

            if not HAS_TQDM and (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(results)}] exportados...")

        except Exception as e:
            logging.error(f"Erro na exportação de {page_data.get('title', '?')}: {e}")

    exporter.build_rag_index(results)

    print(f"\nPronto! {exported} documentos foram preparados.")
    print(f"Os arquivos estão em: {config.RAG_CHUNKS_DIR}")


def phase_embed(args):
    print("\n" + "-" * 40)
    print("Gerando embeddings e salvando no ChromaDB...")
    print("-" * 40)

    collection_name = getattr(args, "collection_name", "wiki_rag")
    chunk_files = []

    for filename in os.listdir(config.RAG_CHUNKS_DIR):
        if filename.endswith(".json"):
            chunk_files.append(os.path.join(config.RAG_CHUNKS_DIR, filename))

    if not chunk_files:
        print("Nenhum chunk encontrado em rag_chunks/. Rode o pipeline completo primeiro.")
        return

    if args.limit:
        chunk_files = chunk_files[:args.limit]

    print(f"Encontrei {len(chunk_files)} chunks para indexar.")

    if getattr(args, "reset_collection", False):
        client = chroma_repo.get_chroma_client()
        try:
            client.delete_collection(collection_name)
            print(f"Coleção '{collection_name}' apagada.")
        except Exception:
            pass  # coleção pode não existir ainda

    collection = chroma_repo.get_or_create_collection(collection_name)
    existing_count = collection.count()
    print(f"Coleção '{collection_name}' tem {existing_count} documentos (após reset).")

    indexed = 0
    errors = 0
    iterator = tqdm(chunk_files, desc="Embedding", unit="chunk") if HAS_TQDM else chunk_files

    for i, filepath in enumerate(iterator):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            content = data.get("content", "")
            title = data.get("title", "")

            if not content:
                continue

            text_chunks = text_utils.split_text_into_chunks(content, title=title)

            ids, embeddings, documents, metadatas = [], [], [], []

            base_meta = {
                k: v for k, v in data.items()
                if k != "content" and isinstance(v, (str, int, float, bool))
            }
            if "categories" in data and isinstance(data["categories"], list):
                base_meta["categories"] = ", ".join(data["categories"])

            for j, chunk_text in enumerate(text_chunks):
                chunk_id = f"{ollama.generate_deterministic_id(chunk_text, title)}_{j}"
                embedding = ollama.generate_embedding(chunk_text)

                meta = base_meta.copy()
                meta["chunk_index"] = j
                meta["total_chunks"] = len(text_chunks)

                ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(chunk_text)
                metadatas.append(meta)

            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            indexed += 1

            if not HAS_TQDM and (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(chunk_files)}] indexados...")

        except Exception as e:
            errors += 1
            logging.error(f"Erro no embedding de {filepath}: {e}")

    final_count = collection.count()
    print(f"\nIndexação finalizada: {indexed} documentos processados, {errors} erros.")
    print(f"Total no ChromaDB ('{collection_name}'): {final_count} chunks.")


def _load_existing_results() -> list[dict]:
    results = []
    json_dir = config.JSON_OUTPUT_DIR
    if not os.path.exists(json_dir):
        return results

    for filename in os.listdir(json_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(json_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append(data)
            except Exception:
                continue

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline de scraping da Wiki Valheim para RAG"
    )
    parser.add_argument(
        "--discover-only", action="store_true",
        help="Só executa a fase de descoberta de páginas"
    )
    parser.add_argument(
        "--scrape-only", action="store_true",
        help="Só executa o scraping (requer manifesto existente)"
    )
    parser.add_argument(
        "--export-only", action="store_true",
        help="Só exporta para RAG (requer JSONs existentes em data/json/)"
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limita o número de páginas a processar"
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="Filtra por nome de categoria/slug"
    )
    parser.add_argument(
        "--embed-only", action="store_true",
        help="Só gera embeddings e salva no ChromaDB (requer rag_chunks existentes)"
    )
    parser.add_argument(
        "--collection-name", type=str, default="wiki_rag",
        help="Nome da coleção no ChromaDB (padrão: wiki_rag)"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Ignora progresso salvo e recomeça do zero"
    )
    parser.add_argument(
        "--reset-collection", action="store_true",
        help="Apaga a coleção do ChromaDB antes de indexar (use ao reindexar do zero)"
    )

    args = parser.parse_args()
    _setup_logging()
    config.ensure_dirs()

    start_total = time.time()

    print("-" * 40)
    print("Sistema de Extração Wiki Valheim → RAG")
    print("-" * 40)

    if args.reset and os.path.exists(config.PROGRESS_PATH):
        os.remove(config.PROGRESS_PATH)
        print("Histórico de progresso removido.")

    if args.embed_only:
        phase_embed(args)

    elif args.export_only:
        results = _load_existing_results()
        if not results:
            print("Não encontrei arquivos JSON em data/json/. Precisa rodar o carregamento primeiro.")
            sys.exit(1)
        phase_export(args, results)

    elif args.scrape_only:
        if not os.path.exists(config.PAGE_MANIFEST_PATH):
            print("Manifesto não encontrado. Tente rodar com --discover-only antes.")
            sys.exit(1)
        with open(config.PAGE_MANIFEST_PATH, "r", encoding="utf-8") as f:
            pages = json.load(f)
        results = phase_scrape(args, pages)
        phase_export(args, results)

    elif args.discover_only:
        phase_discover(args)

    else:
        pages = phase_discover(args)
        results = phase_scrape(args, pages)
        phase_export(args, results)
        phase_embed(args)

    elapsed = time.time() - start_total
    print(f"\nProcesso finalizado em {elapsed:.1f}s.")
    print("-" * 40)


if __name__ == "__main__":
    main()
