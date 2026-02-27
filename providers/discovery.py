import os
import json
import time
import random

import cloudscraper
from bs4 import BeautifulSoup

from core import config


def _create_scraper():
    return cloudscraper.create_scraper(browser=config.BROWSER_CONFIG)


def _delay():
    time.sleep(random.uniform(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS))


def _is_valid_wiki_url(href: str) -> bool:
    if not href or not href.startswith("/wiki/"):
        return False
    for prefix in config.IGNORE_URL_PREFIXES:
        if href.startswith(prefix):
            return False
    if "action=edit" in href or "redlink=1" in href:
        return False
    return True


def _extract_page_links(soup) -> list[dict]:
    pages = []
    seen_urls = set()

    content = soup.find("div", id="mw-content-text")
    if not content:
        return pages

    for a_tag in content.find_all("a", href=True):
        href = a_tag["href"]
        if not _is_valid_wiki_url(href):
            continue

        full_url = config.BASE_URL + href
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        title = a_tag.get("title", "") or a_tag.text.strip()
        if title:
            pages.append({
                "title": title,
                "url": full_url,
                "slug": href.replace("/wiki/", ""),
            })

    return pages


def discover_from_category(scraper, category_slug: str) -> list[dict]:
    pages = []
    url = f"{config.WIKI_BASE}/{category_slug}"

    while url:
        print(f"  Verificando categoria: {url}")
        try:
            resp = scraper.get(url)
            if resp.status_code != 200:
                print(f"    Problema no status {resp.status_code}")
                break

            soup = BeautifulSoup(resp.text, "html.parser")

            cat_div = soup.find("div", class_="category-page__members")
            if cat_div:
                for a_tag in cat_div.find_all("a", href=True):
                    href = a_tag["href"]
                    if _is_valid_wiki_url(href):
                        full_url = config.BASE_URL + href
                        title = a_tag.get("title", "") or a_tag.text.strip()
                        slug = href.replace("/wiki/", "")
                        pages.append({
                            "title": title,
                            "url": full_url,
                            "slug": slug,
                        })

            if not pages:
                mw_pages = soup.find("div", id="mw-pages")
                if mw_pages:
                    for a_tag in mw_pages.find_all("a", href=True):
                        href = a_tag["href"]
                        if _is_valid_wiki_url(href):
                            full_url = config.BASE_URL + href
                            title = a_tag.get("title", "") or a_tag.text.strip()
                            slug = href.replace("/wiki/", "")
                            pages.append({
                                "title": title,
                                "url": full_url,
                                "slug": slug,
                            })

            next_link = soup.find("a", class_="category-page__pagination-next")
            if next_link and next_link.get("href"):
                url = config.BASE_URL + next_link["href"]
                _delay()
            else:
                url = None

        except Exception as e:
            print(f"    Erro inesperado: {e}")
            break

    return pages


def discover_from_index_page(scraper, page_slug: str) -> list[dict]:
    url = f"{config.WIKI_BASE}/{page_slug}"
    print(f"  Lendo página de índice: {url}")

    try:
        resp = scraper.get(url)
        if resp.status_code != 200:
            print(f"    Problema no status {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        pages = [{
            "title": page_slug.replace("_", " "),
            "url": url,
            "slug": page_slug,
        }]

        pages.extend(_extract_page_links(soup))
        return pages

    except Exception as e:
        print(f"    Erro inesperado: {e}")
        return []


def discover_all_pages(use_cache: bool = False) -> list[dict]:
    config.ensure_dirs()

    if use_cache and os.path.exists(config.PAGE_MANIFEST_PATH):
        print("Carregando lista de páginas do cache...")
        with open(config.PAGE_MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    scraper = _create_scraper()
    all_pages = []
    seen_urls = set()

    def _add_pages(new_pages):
        for p in new_pages:
            if p["url"] not in seen_urls:
                seen_urls.add(p["url"])
                all_pages.append(p)

    print("\nBuscando páginas por categorias...")
    for cat in config.CATEGORY_PAGES:
        pages = discover_from_category(scraper, cat)
        _add_pages(pages)
        print(f"    → {len(pages)} páginas em {cat}")
        _delay()

    print("\nBuscando páginas através dos índices centrais...")
    for idx_page in config.INDEX_PAGES:
        pages = discover_from_index_page(scraper, idx_page)
        _add_pages(pages)
        print(f"    → {len(pages)} páginas via {idx_page}")
        _delay()

    with open(config.PAGE_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, indent=2, ensure_ascii=False)

    print(f"\nLista de páginas pronta: {len(all_pages)} itens únicos encontrados.")
    print(f"Documento salvo em: {config.PAGE_MANIFEST_PATH}")

    return all_pages


if __name__ == "__main__":
    pages = discover_all_pages()
    print(f"\nTotal de páginas descobertas: {len(pages)}")
    for p in pages[:10]:
        print(f"  - {p['title']} ({p['url']})")
    if len(pages) > 10:
        print(f"  ... e mais {len(pages) - 10}")
