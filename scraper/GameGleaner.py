import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
from datetime import datetime

# -----------------------------
# CONFIG
# -----------------------------
BASE_DIR = "data"
THUMB_DIR = os.path.join(BASE_DIR, "thumbnails")
CSV_FILE = os.path.join(BASE_DIR, "itch_games.csv")
os.makedirs(THUMB_DIR, exist_ok=True)

POPULAR_URL = "https://itch.io/games/popular"
TOP_SELLERS_URL = "https://itch.io/games/top-sellers"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def download_thumbnail(url, title):
    ext = url.split('.')[-1].split('?')[0]
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
    path = os.path.join(THUMB_DIR, f"{datetime.today().strftime('%Y-%m-%d')}_{safe_title}.{ext}")
    try:
        resp = requests.get(url, headers=HEADERS)
        with open(path, "wb") as f:
            f.write(resp.content)
        return path
    except Exception as e:
        print(f"Thumbnail download failed: {e}")
        return ""

def parse_price(title_text, price_text=None):
    """
    Always separate price from title.
    """
    price = None
    if price_text and price_text.strip():
        price = price_text.strip()
    else:
        # fallback: parse from title if inline
        match = re.search(r'(\$|£|€)\d+(\.\d{1,2})?', title_text)
        if match:
            price = match.group(0)
            title_text = title_text.replace(price, "").strip()
    is_free = price in (None, "", "Free")
    return title_text, price, is_free

def scrape_page(url, listing_type):
    page_num = 1
    results = []

    while url:
        print(f"Scraping {listing_type} page {page_num}: {url}")
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        for game in soup.select(".game_cell"):
            title_tag = game.select_one(".title .game_title")
            author_tag = game.select_one(".game_author")
            price_tag = game.select_one(".price")
            thumb_tag = game.select_one("img.cover_image")

            if not title_tag:
                continue

            title_raw = title_tag.text.strip()
            author = author_tag.text.strip() if author_tag else ""
            price_text = price_tag.text.strip() if price_tag else None
            title, price, is_free = parse_price(title_raw, price_text)

            thumb_url = thumb_tag["src"] if thumb_tag else ""
            thumb_path = download_thumbnail(thumb_url, title) if thumb_url else ""

            results.append({
                "title": title,
                "url": game.select_one("a")["href"],
                "author": author,
                "price": price,
                "currency": price[0] if price and price[0] in "$£€" else "",
                "is_free": is_free,
                "thumbnail_url": thumb_url,
                "thumbnail_path": thumb_path,
                "scrape_date": datetime.today().strftime("%Y-%m-%d"),
                "listing_type": listing_type,
                "source_page": f"{listing_type}_page_{page_num}"
            })

        # Check for next page
        next_btn = soup.select_one(".next_page")
        url = next_btn["href"] if next_btn else None
        page_num += 1

    return results

# -----------------------------
# MAIN SCRAPER
# -----------------------------
all_results = []

# Scrape popular
all_results += scrape_page(POPULAR_URL, "popular")

# Scrape top sellers
all_results += scrape_page(TOP_SELLERS_URL, "top_sellers")

# -----------------------------
# SAVE TO CSV
# -----------------------------
df = pd.DataFrame(all_results)

# If CSV exists, append new data and deduplicate by URL
if os.path.exists(CSV_FILE):
    old_df = pd.read_csv(CSV_FILE)
    df = pd.concat([old_df, df])
    df.drop_duplicates(subset=["url", "scrape_date"], inplace=True)

df.to_csv(CSV_FILE, index=False)
print(f"Saved {len(df)} records to {CSV_FILE}")
