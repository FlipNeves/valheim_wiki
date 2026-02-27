import re


def split_text_into_chunks(text: str, max_chars: int = 1500, overlap: int = 200, title: str = "") -> list[str]:
    if not text:
        return []

    prefix = f"[Título: {title}]\n" if title else ""

    if len(text) <= max_chars:
        return [prefix + text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + max_chars

        if end >= text_len:
            chunks.append(text[start:])
            break

        search_start = max(start, end - int(max_chars * 0.2))
        slice_to_search = text[search_start:end]

        paragraph_break = slice_to_search.rfind('\n\n')
        if paragraph_break != -1:
            split_point = search_start + paragraph_break + 2
        else:
            newline_break = slice_to_search.rfind('\n')
            if newline_break != -1:
                split_point = search_start + newline_break + 1
            else:
                sentence_break = -1
                for char in ['. ', '! ', '? ']:
                    pos = slice_to_search.rfind(char)
                    if pos > sentence_break:
                        sentence_break = pos

                if sentence_break != -1:
                    split_point = search_start + sentence_break + 1
                else:
                    space_break = slice_to_search.rfind(' ')
                    if space_break != -1:
                        split_point = search_start + space_break + 1
                    else:
                        split_point = end

        chunks.append(text[start:split_point].strip())
        start = max(start + 1, split_point - overlap)

    return [prefix + c for c in chunks if c.strip()]
