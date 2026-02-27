import os

BASE_URL = "https://valheim.fandom.com"
WIKI_BASE = f"{BASE_URL}/wiki"

CATEGORY_PAGES = [
    "Category:Biomes",
    "Category:Creatures",
    "Category:Weapons",
    "Category:Armor",
    "Category:Food",
    "Category:Resources",
    "Category:Building",
    "Category:Bosses",
    "Category:Tools",
    "Category:Arrows",
    "Category:Shields",
    "Category:Potions",
    "Category:Furniture",
    "Category:Events",
    "Category:Skills",
]

INDEX_PAGES = [
    "Meadows", "Black_Forest", "Swamp", "Mountains", "Plains",
    "Mistlands", "Ashlands", "Deep_North", "Ocean",
    "Damage_types", "Status_effects", "Comfort", "Recipes",
    "Weapons", "Armor", "Food", "Taming", "Farming",
    "Building", "Crafting", "Fishing", "Skills",
    "Trader", "Boss", "World_modifiers",
]

MIN_DELAY_SECONDS = 2.0
MAX_DELAY_SECONDS = 5.0

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
JSON_OUTPUT_DIR = os.path.join(DATA_DIR, "json")
RAG_CHUNKS_DIR = os.path.join(DATA_DIR, "rag_chunks")

PAGE_MANIFEST_PATH = os.path.join(DATA_DIR, "page_manifest.json")
RAG_INDEX_PATH = os.path.join(DATA_DIR, "rag_index.json")
PROGRESS_PATH = os.path.join(DATA_DIR, "progress.json")
ERROR_LOG_PATH = os.path.join(DATA_DIR, "errors.log")

BROWSER_CONFIG = {
    "browser": "chrome",
    "platform": "windows",
    "desktop": True,
}

IGNORE_URL_PREFIXES = [
    "/wiki/Special:",
    "/wiki/User:",
    "/wiki/Talk:",
    "/wiki/Template:",
    "/wiki/Category:",
    "/wiki/File:",
    "/wiki/MediaWiki:",
    "/wiki/Module:",
    "/wiki/Thread:",
    "/wiki/Message_Wall:",
    "/wiki/Board:",
    "/wiki/User_blog:",
]

IGNORE_SECTIONS = [
    "References",
    "External links",
    "Navigation",
    "See also",
    "Gallery",
    "Videos",
    "Comments",
]


def ensure_dirs():
    for d in [DATA_DIR, JSON_OUTPUT_DIR, RAG_CHUNKS_DIR]:
        os.makedirs(d, exist_ok=True)
