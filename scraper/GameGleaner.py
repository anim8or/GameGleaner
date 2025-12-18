import os
import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- Paths ---
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(REPO_ROOT, "data")
THUMB_DIR = os.path.join(REPO_ROOT, "thumbnails")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

CSV_PATH = os.path.join(DATA_DIR, "itch_games.csv")

# --- URLs ---
POPULAR_URL = "https://itch.io/games/popular"
TOP_SELLERS_URL = "https://itch.io/games/top-sellers"

# --- Scraper functions ---
def scrape_page(url, listing_type):
    print(f"Scraping {listing_type} page: {url}")
    results = []
    resp = requests.get(url)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Loop through each game card
    game_cards = soup.select("div.game_cell")  # adjust selector if needed
    for card in game_cards:
        title_tag = card.select_one("a.title")
        title = title_tag.text.strip() if title_tag else "Unknown"
        game_url = title_tag['href'] if title_tag else ""
        author_tag = card.select_one("div.author")
        author = author_tag.text.strip() if author_tag else ""
        price_tag = card.select_one("div.price")
        price = price_tag.text.strip() if price_tag else "Free"
        is_free = price.lower() == "free"
        thumbnail_tag = card.select_one("img.cover")
        thumbnail_url = thumbnail_tag['src'] if thumbnail_tag else ""
        genre_tag = card.select_one("div.genre")
        genre = genre_tag.text.strip() if genre_tag else ""

        # Save thumbnail
        thumb_path = ""
        if thumbnail_url:
            filename = f"{datetime.today().strftime('%Y-%m-%d')}_{title.replace(' ', '_')}.png"
            thumb_path = os.path.join(THUMB_DIR, filename)
            try:
                r = requests.get(thumbnail_url)
                with open(thumb_path, "wb") as f:
                    f.write(r.content)
            except Exception as e:
                print(f"Failed to download thumbnail: {e}")

        results.append({
            "title": title,
            "url": game_url,
            "author": author,
            "price": price,
            "currency": "",  # could parse from price if needed
            "is_free": is_free,
            "genre": genre,
            "thumbnail_url": thumbnail_url,
            "thumbnail_path": thumb_path,
            "scrape_date": datetime.today().strftime("%Y-%m-%d"),
            "listing_type": listing_type,
            "source_page": url.split("/")[-1]
        })
    
    return results

# --- Main ---
if __name__ == "__main__":
    all_results = []
    for url, listing_type in [(POPULAR_URL, "popular"), (TOP_SELLERS_URL, "top_sellers")]:
        try:
            all_results += scrape_page(url, listing_type)
        except Exception as e:
            print(f"Error scraping {listing_type}: {e}")

    # Write CSV
    keys = ["title","url","author","price","currency","is_free","genre","thumbnail_url","thumbnail_path","scrape_date","listing_type","source_page"]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(all_results)

    print(f"Scrape complete. CSV saved to {CSV_PATH}")
