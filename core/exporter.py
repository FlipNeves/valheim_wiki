import json
import os
import re

from core import config


def _slug_to_filename(slug: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*]', "_", slug)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return safe.lower()


def export_page_json(page_data: dict) -> str:
    config.ensure_dirs()
    filename = _slug_to_filename(page_data["slug"]) + ".json"
    filepath = os.path.join(config.JSON_OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(page_data, f, indent=2, ensure_ascii=False)

    return filepath


def _build_rag_text(page_data: dict) -> str:
    parts = []

    title = page_data.get("title", "")
    parts.append(f"# {title}")

    infobox = page_data.get("infobox", {})
    if infobox:
        infobox_lines = []
        for key, value in infobox.items():
            if not key.startswith("_"):
                infobox_lines.append(f"{key}: {value}")
        if infobox_lines:
            parts.append(" | ".join(infobox_lines))

    sections = page_data.get("sections", [])
    for section in sections:
        heading = section.get("heading", "")
        level = section.get("level", 2)
        text = section.get("text", "")

        md_header = "#" * level
        parts.append(f"{md_header} {heading}")

        if text:
            parts.append(text)

        table_data = section.get("table_data", [])
        if table_data:
            for row in table_data:
                row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
                if row_text:
                    parts.append(f"• {row_text}")

    categories = page_data.get("categories", [])
    if categories:
        parts.append(f"Categorias: {', '.join(categories)}")

    return "\n\n".join(parts)


def export_rag_chunk(page_data: dict) -> str:
    config.ensure_dirs()

    rag_text = _build_rag_text(page_data)
    filename = _slug_to_filename(page_data["slug"]) + ".json"
    filepath = os.path.join(config.RAG_CHUNKS_DIR, filename)

    chunk_obj = {
        "title": page_data.get("title", ""),
        "url": page_data.get("url", ""),
        "slug": page_data.get("slug", ""),
        "categories": page_data.get("categories", []),
        "content": rag_text,
        "content_length": len(rag_text),
        "scraped_at": page_data.get("scraped_at", ""),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(chunk_obj, f, indent=2, ensure_ascii=False)

    return filepath


def export_page(page_data: dict) -> tuple[str, str]:
    json_path = export_page_json(page_data)
    chunk_path = export_rag_chunk(page_data)
    return json_path, chunk_path


def build_rag_index(pages_data: list[dict]) -> str:
    config.ensure_dirs()

    index = []
    for page in pages_data:
        index.append({
            "title": page.get("title", ""),
            "url": page.get("url", ""),
            "slug": page.get("slug", ""),
            "categories": page.get("categories", []),
            "has_infobox": bool(page.get("infobox")),
            "section_count": len(page.get("sections", [])),
            "full_text_length": len(page.get("full_text", "")),
            "scraped_at": page.get("scraped_at", ""),
        })

    with open(config.RAG_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"📇 Índice RAG salvo: {len(index)} documentos → {config.RAG_INDEX_PATH}")
    return config.RAG_INDEX_PATH


if __name__ == "__main__":
    sample = {
        "title": "Iron Mace",
        "url": "https://valheim.fandom.com/wiki/Iron_mace",
        "slug": "Iron_mace",
        "categories": ["Weapons", "Maces"],
        "infobox": {
            "Type": "Mace",
            "Damage": "55 Blunt",
            "Crafting Station": "Forge",
        },
        "sections": [
            {
                "heading": "Description",
                "level": 2,
                "text": "The Iron Mace is a powerful blunt weapon.",
            },
            {
                "heading": "Crafting",
                "level": 2,
                "text": "Requires a Forge level 2.",
                "table_data": [
                    {"Material": "Iron", "Amount": "20"},
                    {"Material": "Wood", "Amount": "4"},
                ],
            },
        ],
        "full_text": "Iron Mace. The Iron Mace is a powerful blunt weapon.",
        "scraped_at": "2026-02-09T23:00:00+00:00",
    }

    json_path, chunk_path = export_page(sample)
    print(f"✅ JSON: {json_path}")
    print(f"✅ Chunk: {chunk_path}")

    with open(chunk_path, "r", encoding="utf-8") as f:
        chunk = json.load(f)
    print(f"\n--- RAG Chunk ---")
    print(chunk["content"])
