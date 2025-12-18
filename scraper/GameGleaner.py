# scraper/GameGleaner.py
import requests
import pandas as pd
import os
from datetime import datetime
from urllib.parse import urlparse

# ---------- CONFIG ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
THUMBNAIL_DIR = os.path.join(BASE_DIR, "data", "thumbnails")
CSV_FILE = os.path.join(BASE_DIR, "data", "itch_games.csv")

os.makedirs(THUMBNAIL_DIR, exist_ok=True)
SCRAPE_DATE = datetime.today().strftime("%Y-%m-%d")

LISTINGS = [
    {"type": "popular", "url": "https://itch.io/games/popular?page={}&format=json"},
    {"type": "top_sellers", "url": "https://itch.io/games/top-sellers?page={}&format=json"}
]

# ---------- FUNCTIONS ----------
def download_thumbnail(url, title):
    if not url:
        return ""
    filename = f"{SCRAPE_DATE}_{title}".replace(" ", "_").replace("/", "_")
    ext = os.path.splitext(urlparse(url).path)[1]
    filepath = os.path.join(THUMBNAIL_DIR, f"{filename}{ext}")
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(r.content)
        return filepath
    except Exception as e:
        print(f"Failed to download thumbnail for {title}: {e}")
        return ""

def scrape_listing(listing_type, url_template):
    results = []
    page = 1
    while True:
        url = url_template.format(page)
        print(f"Scraping {listing_type} page {page}: {url}")
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Error fetching JSON: {e}")
            break

        games = data.get("games", [])
        if not games:
            break

        for game in games:
            title = game.get("title", "Unknown")
            game_url = game.get("url")
            author = game.get("user", {}).get("username")
            price_cents = game.get("price_cents", 0)
            currency = game.get("currency")
            is_free = game.get("free", True)
            display_price = game.get("display_price", "")
            genres = ", ".join([g["name"] for g in game.get("genres", [])])
            thumbnail_url = game.get("cover_url")
            thumbnail_path = download_thumbnail(thumbnail_url, title)

            results.append({
                "title": title,
                "url": game_url,
                "author": author,
                "price": display_price,
                "currency": currency,
                "is_free": is_free,
                "genre": genres,
                "thumbnail_url": thumbnail_url,
                "thumbnail_path": thumbnail_path,
                "scrape_date": SCRAPE_DATE,
                "listing_type": listing_type,
                "source_page": f"{listing_type}_page_{page}"
            })
        page += 1
    return results

# ---------- MAIN ----------
if __name__ == "__main__":
    all_results = []
    for listing in LISTINGS:
        all_results += scrape_listing(listing["type"], listing["url"])

    if all_results:
        df_new = pd.DataFrame(all_results)
        if os.path.exists(CSV_FILE):
            df_existing = pd.read_csv(CSV_FILE)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new
        df_combined.to_csv(CSV_FILE, index=False)
        print(f"Scraped {len(all_results)} games. Saved to {CSV_FILE}")
    else:
        print("No games scraped.")
