import hashlib
from typing import Optional
import ollama


EMBED_MODEL = "nomic-embed-text-v2-moe"
CHAT_MODEL = "llama3"
TRANSLATE_MODEL = "llama3"  # mesmo modelo; troque para um menor se quiser mais velocidade

SYSTEM_PROMPT = """
Você é um assistente especializado no jogo Valheim.

REGRAS ABSOLUTAS — siga sem exceção:

1. USE APENAS o conteúdo entre [INÍCIO DO CONTEXTO] e [FIM DO CONTEXTO] para responder.
2. Se a resposta não estiver EXPLICITAMENTE escrita no contexto, responda somente:
   "Não encontrei essa informação na wiki."
3. NUNCA invente, suponha, deduza ou complete informações ausentes no contexto.
4. NUNCA mencione wiki, fonte, contexto, documentos ou de onde veio a informação.
5. NUNCA use seu conhecimento interno sobre Valheim ou jogos de sobrevivência.
6. Não traduza nomes de itens, criaturas, armas, estruturas ou locais, exceto se já
   traduzidos no próprio contexto.
7. Escreva a resposta em português brasileiro.
8. Seja direto. Não adicione prefácios, conclusões genéricas nem frases como
   "espero ter ajudado" ou "essa informação está disponível em...".
9. Você já está sendo usado no contexto de uma wiki de Valheim, não seja redundante.
"""


def generate_deterministic_id(content: str, title: str) -> str:
    raw_data = f"{title}|{content}"
    return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()

def translate_text(text: str, target_lang: str = "en", model: str = TRANSLATE_MODEL) -> str:
    """Translate *text* to *target_lang* ('en' or 'pt-BR') using the local LLM.

    Uses generate() instead of chat() for lower overhead on short outputs.
    Returns the translated string, or the original text if translation fails.
    """
    lang_label = "English" if target_lang == "en" else "Brazilian Portuguese"
    prompt = (
        f"Translate to {lang_label}. Output ONLY the translated text, no explanations.\n"
        f"Text: {text}\n"
        "Translation:"
    )
    try:
        response = ollama.generate(model=model, prompt=prompt)
        return response["response"].strip()
    except Exception:
        return text  # fallback: retorna o original se a tradução falhar



def generate_embedding(text: str, model: str = EMBED_MODEL) -> list[float]:
    response = ollama.embeddings(model=model, prompt=text)
    return response["embedding"]


def chat_with_context(
    question: str,
    context_chunks: list[str],
    history: Optional[list[dict]] = None,
    model: str = CHAT_MODEL,
) -> str:
    parts = []
    for chunk in context_chunks:
        if isinstance(chunk, dict):
            text = chunk.get("content", "")
        else:
            text = chunk
        if text:
            parts.append(text)
    context_block = "\n\n---\n\n".join(parts)

    user_message = f"""[INÍCIO DO CONTEXTO]
{context_block}
[FIM DO CONTEXTO]

Pergunta: {question}"""

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": user_message})

    response = ollama.chat(model=model, messages=messages)
    return response["message"]["content"]
