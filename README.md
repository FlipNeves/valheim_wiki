# Valheim Wiki Scraper → RAG Chatbot

Este projeto automatiza a extração de dados da [Valheim Wiki](https://valheim.fandom.com/wiki/Valheim_Wiki) e os transforma em um **chatbot inteligente** usando RAG (Retrieval-Augmented Generation). Ele faz scraping, limpeza, chunking, embedding e indexação — e depois responde perguntas usando uma LLM local via Ollama.

## Pré-requisitos

- Python 3.10+
- [Ollama](https://ollama.ai) rodando localmente com os modelos:
  ```bash
  ollama pull nomic-embed-text-v2-moe   # Para embeddings
  ollama pull llama3                      # Para gerar respostas
  ```

## Como começar

Instale as dependências:
```bash
pip install -r requirements.txt
```

## Como usar

### Pipeline completo (scraping → embedding)

O `pipeline.py` orquestra todo o fluxo de ponta a ponta — da descoberta de páginas até a indexação no ChromaDB. Cada etapa pode ser executada separadamente:

```bash
python pipeline.py                                    # Processo completo (descoberta + extração + embedding)
python pipeline.py --discover-only                    # Apenas mapeia quais páginas existem
python pipeline.py --scrape-only                      # Extrai o conteúdo (precisa ter feito a descoberta antes)
python pipeline.py --export-only                      # Só exporta para RAG (requer JSONs existentes)
python pipeline.py --embed-only                       # Só gera embeddings e salva no ChromaDB
python pipeline.py --limit 5                          # Processa apenas 5 páginas (bom para testes)
python pipeline.py --category Weapons                 # Foca em uma categoria específica
python pipeline.py --reset                            # Ignora progresso salvo e recomeça do zero
python pipeline.py --reset-collection                 # Apaga a coleção do ChromaDB e reindexa do zero
python pipeline.py --collection-name minha_colecao   # Define um nome personalizado para a coleção (padrão: wiki_rag)
```

### Chatbot no terminal

Depois que o pipeline terminar, converse com o chatbot:

```bash
python chat.py
```

### API REST

Suba o servidor para acessar via HTTP:

```bash
uvicorn api.main:app --reload
```

Endpoints disponíveis em `http://localhost:8000/docs`:
- `POST /collection/init` — Inicializa a coleção no ChromaDB
- `POST /scrape/discover` — Mapeia páginas da wiki
- `POST /scrape/extract` — Extrai e indexa uma URL
- `POST /process/embed` — Processa chunks locais em batch
- `GET /rag/documents` — Lista documentos indexados
- `POST /rag/ask` — **Faz uma pergunta ao chatbot**

## Estrutura do Projeto

```
├── pipeline.py         # Pipeline CLI (scraping → embedding)
├── chat.py             # Chatbot interativo no terminal
├── api/                # Interface FastAPI (endpoints HTTP)
├── services/           # Lógica de orquestração do RAG
├── repositories/       # Integração com ChromaDB
├── providers/          # Integrações externas (Scraper, Ollama)
├── core/               # Configurações, exportadores e utilitários
├── domain/             # Modelos de dados (Pydantic)
└── data/
    ├── json/           # Conteúdo bruto de cada página
    ├── rag_chunks/     # Texto otimizado para busca
    └── chroma_db/      # Banco de dados vetorial (índices)
```

