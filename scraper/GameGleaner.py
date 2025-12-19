import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
from datetime import datetime
from urllib.parse import urljoin
from pathlib import Path
import re

# =========================
# CONFIG
# =========================

POPULAR_URL = "https://itch.io/games/popular"
TOP_SELLERS_URL = "https://itch.io/games/top-sellers"

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
THUMBNAIL_DIR = DATA_DIR / "thumbnails"
CSV_PATH = DATA_DIR / "itch_games.csv"

HEADERS = {
    "User-Agent": "GameGleanerBot/1.0 (research; respectful scraping)"
}

MAX_PAGES = 2
REQUEST_DELAY = 1.5

# =========================
# UTILS
# =========================

def safe_text(el):
    return el.get_text(strip=True) if el else None

def ensure_dirs():
    DATA_DIR.mkdir(exist_ok=True)
    THUMBNAIL_DIR.mkdir(exist_ok=True)

def parse_price(text):
    if not text:
        return 0, None, True

    text = text.replace(",", "").strip()

    if "Free" in text:
        return 0, None, True

    match = re.search(r"([£$€])\s*([\d.]+)", text)
    if match:
        symbol, amount = match.groups()
        return float(amount), symbol, False

    return 0, None, True

# =========================
# LISTING PAGE SCRAPER
# =========================

def scrape_listing_page(start_url, listing_type):
    results = []
    url = start_url

    for page in range(1, MAX_PAGES + 1):
        print(f"Scraping {listing_type} page {page}: {url}")
        resp = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")

        games = soup.select(".game_cell")
        for game in games:
            title_el = game.select_one(".title")
            link_el = game.select_one("a")

            title = safe_text(title_el) or "Unknown"
            game_url = link_el["href"] if link_el and link_el.has_attr("href") else None

            if game_url:
                results.append({
                    "title": title,
                    "url": game_url,
                    "listing_type": listing_type,
                    "source_page": f"{listing_type}_page_{page}",
                    "scrape_date": datetime.utcnow().date().isoformat()
                })

        next_btn = soup.select_one("a.next_page")
        url = next_btn["href"] if next_btn and next_btn.has_attr("href") else None
        if not url:
            break

        time.sleep(REQUEST_DELAY)

    return results

# =========================
# PER-GAME SCRAPER
# =========================

def scrape_game_page(game_url):
    resp = requests.get(game_url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Author
    author = safe_text(soup.select_one(".game_author a"))

    # Genre / tags
    genres = [safe_text(t) for t in soup.select(".game_genre a")]
    tags = [safe_text(t) for t in soup.select(".game_tags a")]
    genre = "|".join(filter(None, set(genres + tags)))

    # Price
    price_el = soup.select_one(".price_value") or soup.select_one(".buy_btn")
    price_text = safe_text(price_el)
    price, currency, is_free = parse_price(price_text)

    # Thumbnail
    thumb_url = None
    thumb_meta = soup.find("meta", property="og:image")
    if thumb_meta and thumb_meta.has_attr("content"):
        thumb_url = thumb_meta["content"]

    thumb_path = None
    if thumb_url:
        filename = thumb_url.split("/")[-1].split("?")[0]
        thumb_path = THUMBNAIL_DIR / filename
        if not thumb_path.exists():
            try:
                img = requests.get(thumb_url, headers=HEADERS)
                thumb_path.write_bytes(img.content)
            except Exception:
                thumb_path = None

    return {
        "author": author,
        "price": price,
        "currency": currency,
        "is_free": is_free,
        "genre": genre,
        "thumbnail_url": thumb_url,
        "thumbnail_path": str(thumb_path) if thumb_path else None
    }

# =========================
# MAIN
# =========================

def main():
    ensure_dirs()

    rows = []
    rows += scrape_listing_page(POPULAR_URL, "popular")
    rows += scrape_listing_page(TOP_SELLERS_URL, "top_sellers")

    df = pd.DataFrame(rows)
    df.drop_duplicates(subset=["url", "listing_type"], inplace=True)

    enriched = []
    seen = set()

    for _, row in df.iterrows():
        if row["url"] in seen:
            continue

        seen.add(row["url"])
        print(f"Enriching {row['url']}")
        meta = scrape_game_page(row["url"])
        enriched.append({**row, **meta})
        time.sleep(REQUEST_DELAY)

    final_df = pd.DataFrame(enriched)

    if CSV_PATH.exists():
        old = pd.read_csv(CSV_PATH)
        final_df = pd.concat([old, final_df], ignore_index=True)

    final_df.drop_duplicates(
        subset=["url", "listing_type", "scrape_date"],
        inplace=True
    )

    final_df.to_csv(CSV_PATH, index=False)
    print(f"Saved {len(final_df)} rows to {CSV_PATH}")

if __name__ == "__main__":
    main()
