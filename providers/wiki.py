import cloudscraper
from bs4 import BeautifulSoup, NavigableString, Tag
import time
import random
from datetime import datetime, timezone

from core import config


def _create_scraper():
    return cloudscraper.create_scraper(browser=config.BROWSER_CONFIG)


def _delay():
    time.sleep(random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS))


def _clean_header(text: str) -> str:
    for marker in ["[edit | edit source]", "[edit]"]:
        text = text.replace(marker, "")
    # Remover trailing [] que a wiki usa em headings de seções colapsáveis
    # ex: "Gallery[]" -> "Gallery", "Upgrade information[]" -> "Upgrade information"
    text = text.strip()
    if text.endswith("[]"):
        text = text[:-2].strip()
    return text


def _clean_text(text: str) -> str:
    text = " ".join(text.split())
    return text.strip()


def _extract_infobox(soup) -> dict:
    infobox = {}

    aside = soup.find("aside", class_="portable-infobox")
    if not aside:
        return infobox

    title_tag = aside.find("h2", class_="pi-title")
    if title_tag:
        infobox["_infobox_title"] = title_tag.text.strip()

    rows = aside.find_all("div", class_="pi-data")
    for row in rows:
        label_tag = row.find("h3", class_="pi-data-label")
        value_tag = row.find("div", class_="pi-data-value")

        if not (label_tag and value_tag):
            continue

        key = label_tag.text.strip()

        # Caso especial: lista de materiais (ul > li com <a> + texto de quantidade)
        ul = value_tag.find("ul")
        if ul:
            items = []
            for li in ul.find_all("li"):
                parts = []
                for child in li.children:
                    if isinstance(child, Tag):
                        t = child.text.strip()
                        if t:
                            parts.append(t)
                    elif isinstance(child, NavigableString):
                        t = child.strip()
                        if t:
                            parts.append(t)
                item_text = " ".join(parts).strip()
                if item_text:
                    items.append(item_text)
            value = ", ".join(items)
        else:
            value_parts = []
            for child in value_tag.children:
                if isinstance(child, Tag):
                    if child.name == "br":
                        value_parts.append(" | ")
                    elif child.name == "a":
                        t = child.text.strip()
                        if t:
                            value_parts.append(t)
                    else:
                        sub_links = child.find_all("a")
                        if sub_links:
                            for sl in sub_links:
                                st = sl.text.strip()
                                if st:
                                    value_parts.append(st)
                        else:
                            t = child.text.strip()
                            if t:
                                value_parts.append(t)
                else:
                    t = str(child).strip()
                    if t:
                        value_parts.append(t)

            raw = "".join(value_parts)
            if " | " in raw:
                value = raw
            else:
                value = ", ".join(p.strip() for p in value_parts if p.strip())

        value = " ".join(value.split())
        if value:
            infobox[key] = value

    return infobox



def _is_navbox_table(table) -> bool:
    classes = table.get("class", [])
    if any(c in classes for c in ["navbox", "navbox-inner", "navbox-columns"]):
        return True
    first_cell = table.find(["th", "td"])
    if first_cell:
        text = first_cell.text.strip()[:30]
        if "v · d · e" in text or "v ·" in text:
            return True
    for th in table.find_all("th"):
        th_text = th.text.strip()[:30]
        if "v · d · e" in th_text or "v ·" in th_text:
            return True
    return False


def _extract_table_data(table) -> list[dict]:
    if _is_navbox_table(table):
        return []

    rows = table.find_all("tr")
    if not rows:
        return []

    # --- Cabeçalho ---
    header_row = rows[0]
    col_headers = [_clean_text(th.text) for th in header_row.find_all("th")]

    if not col_headers:
        first_cells = rows[0].find_all("td")
        if first_cells:
            col_headers = [_clean_text(c.text) for c in first_cells]
            data_rows = rows[1:]
        else:
            return []
    else:
        data_rows = rows[1:]

    if not col_headers:
        return []

    # Detectar "upgrade table": linhas de dados com <th> como row-label
    # (ex.: Damage, Durability, Materials, Crafting Level)
    has_row_labels = any(row.find("th") for row in data_rows)
    # Níveis de qualidade ficam nas colunas depois da primeira (Quality)
    level_labels = col_headers[1:] if len(col_headers) > 1 else col_headers

    data = []
    for row in data_rows:
        row_th = row.find("th")
        cells = row.find_all("td")

        if not cells:
            continue

        if has_row_labels and row_th:
            # Padrão upgrade table: row-label no <th>, valores nos <td>
            stat_name = _clean_text(row_th.text)
            row_data = {"stat": stat_name}
            for i, cell in enumerate(cells):
                col_label = level_labels[i] if i < len(level_labels) else f"col_{i}"
                # "1" -> "Quality 1" para deixar a chave autoexplicativa
                key = f"Quality {col_label}" if col_label.isdigit() else col_label
                row_data[key] = _clean_text(cell.text)
            data.append(row_data)
        else:
            # Tabela simples — só colunas, sem row-label
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(col_headers):
                    row_data[col_headers[i]] = _clean_text(cell.text)
                else:
                    row_data[f"col_{i}"] = _clean_text(cell.text)
            if any(v for v in row_data.values()):
                data.append(row_data)

    return data


def _extract_categories(soup) -> list[str]:
    categories = []
    cat_links = soup.find("div", class_="page-header__categories")
    if cat_links:
        for a_tag in cat_links.find_all("a"):
            cat_text = a_tag.text.strip()
            if cat_text:
                categories.append(cat_text)

    if not categories:
        cat_div = soup.find("div", id="catlinks")
        if cat_div:
            for a_tag in cat_div.find_all("a"):
                href = a_tag.get("href", "")
                if "/wiki/Category:" in href:
                    categories.append(a_tag.text.strip())

    return categories


def _extract_sections(content_div) -> list[dict]:
    sections = []

    parser_output = content_div.find("div", class_="mw-parser-output")
    if parser_output:
        content_div = parser_output

    current_section = {
        "heading": "Introduction",
        "level": 1,
        "text_parts": [],
        "table_data": [],
    }

    for aside in content_div.find_all("aside", class_="portable-infobox"):
        aside.extract()

    for table in list(content_div.find_all("table")):
        if _is_navbox_table(table):
            table.extract()

    for element in content_div.children:
        if not isinstance(element, Tag):
            continue

        if element.name in ["h2", "h3", "h4"]:
            header_text = _clean_header(element.text)

            if current_section["text_parts"] or current_section["table_data"]:
                if current_section["heading"] not in config.IGNORE_SECTIONS:
                    sections.append(_finalize_section(current_section))

            level = int(element.name[1])
            current_section = {
                "heading": header_text,
                "level": level,
                "text_parts": [],
                "table_data": [],
            }
            continue

        if current_section["heading"] in config.IGNORE_SECTIONS:
            continue

        if element.name == "aside":
            continue

        if element.name == "p":
            text = _clean_text(element.text)
            if text and len(text) > 5:
                current_section["text_parts"].append(text)

        elif element.name in ["ul", "ol"]:
            items = element.find_all("li", recursive=False)
            for li in items:
                text = _clean_text(li.text)
                if text:
                    current_section["text_parts"].append(f"• {text}")

        elif element.name == "table":
            table_data = _extract_table_data(element)
            if table_data:
                current_section["table_data"].extend(table_data)

        elif element.name == "div":
            for sub_table in element.find_all("table", recursive=True):
                table_data = _extract_table_data(sub_table)
                if table_data:
                    current_section["table_data"].extend(table_data)

    if current_section["text_parts"] or current_section["table_data"]:
        if current_section["heading"] not in config.IGNORE_SECTIONS:
            sections.append(_finalize_section(current_section))

    return sections


def _finalize_section(section: dict) -> dict:
    result = {
        "heading": section["heading"],
        "level": section["level"],
        "text": "\n".join(section["text_parts"]),
    }
    if section["table_data"]:
        result["table_data"] = section["table_data"]
    return result


def scrape_page(url: str, scraper=None) -> dict | None:
    if scraper is None:
        scraper = _create_scraper()

    try:
        response = scraper.get(url)
        if response.status_code != 200:
            print(f"  Aviso: Status {response.status_code} para {url}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("h1", id="firstHeading") or soup.find("h1")
        title = title_tag.text.strip() if title_tag else url.split("/wiki/")[-1].replace("_", " ")

        slug = url.split("/wiki/")[-1] if "/wiki/" in url else title.replace(" ", "_")

        infobox = _extract_infobox(soup)

        content_div = soup.find("div", id="mw-content-text")
        sections = []
        if content_div:
            sections = _extract_sections(content_div)

        categories = _extract_categories(soup)

        full_text_parts = [title]

        if infobox:
            infobox_text = " | ".join(
                f"{k}: {v}" for k, v in infobox.items()
                if not k.startswith("_")
            )
            if infobox_text:
                full_text_parts.append(infobox_text)

        for section in sections:
            if section["text"]:
                full_text_parts.append(f"{section['heading']}. {section['text']}")

        full_text = "\n\n".join(full_text_parts)

        return {
            "title": title,
            "url": url,
            "slug": slug,
            "categories": categories,
            "infobox": infobox,
            "sections": sections,
            "full_text": full_text,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        print(f"  Erro ao processar {url}: {e}")
        return None


def scrape_pages(urls: list[str], scraper=None) -> list[dict]:
    if scraper is None:
        scraper = _create_scraper()

    results = []
    for i, url in enumerate(urls):
        print(f"  [{i+1}/{len(urls)}] Lendo {url}")
        data = scrape_page(url, scraper)
        if data:
            results.append(data)
        if i < len(urls) - 1:
            _delay()

    return results


if __name__ == "__main__":
    test_url = "https://valheim.fandom.com/wiki/Iron_mace"
    print(f"Testando extração de: {test_url}")
    result = scrape_page(test_url)
    if result:
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2000])
        print(f"\nSucesso ao ler: {result['title']}")
        print(f"   Seções: {len(result['sections'])}")
        print(f"   Infobox keys: {list(result['infobox'].keys())}")
        print(f"   Categorias: {result['categories']}")
        print(f"   full_text: {len(result['full_text'])} chars")
    else:
        print("Falha na extração.")
