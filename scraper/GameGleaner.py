import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
THUMB_DIR = os.path.join(DATA_DIR, "thumbnails")
os.makedirs(THUMB_DIR, exist_ok=True)

POPULAR_URL = "https://itch.io/games/popular"
TOP_SELLERS_URL = "https://itch.io/games/top-sellers"
CSV_FILE = os.path.join(DATA_DIR, "itch_games.csv")

def download_thumbnail(url, title):
    if not url:
        return ""
    ext = url.split(".")[-1].split("?")[0]
    safe_title = "".join(c if c.isalnum() else "_" for c in title)
    path = os.path.join(THUMB_DIR, f"{date.today().isoformat()}_{safe_title}.{ext}")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except Exception as e:
        print(f"Error downloading thumbnail for {title}: {e}")
    return ""

def scrape_page(url, listing_type):
    results = []
    page = 1
    while url:
        print(f"Scraping {listing_type} page {page}: {url}")
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "html.parser")

        game_cards = soup.select("div.game_cell, div.game_card")  # handle multiple class variants
        for card in game_cards:
            title_tag = card.select_one("a.game_title, a.title")
            author_tag = card.select_one("div.game_author a")
            thumb_tag = card.select_one("img.game_thumb, img.screenshot")
            price_tag = card.select_one("div.price, span.price")

            title = title_tag.text.strip() if title_tag else "Unknown"
            game_url = "https://itch.io" + title_tag["href"] if title_tag and title_tag.has_attr("href") else ""
            author = author_tag.text.strip() if author_tag else ""
            thumbnail_url = thumb_tag["src"] if thumb_tag and thumb_tag.has_attr("src") else ""
            thumbnail_path = download_thumbnail(thumbnail_url, title) if thumbnail_url else ""
            price = price_tag.text.strip() if price_tag else "Free"

            results.append({
                "title": title,
                "url": game_url,
                "author": author,
                "price": price,
                "currency": "",  # optional: parse from price
                "is_free": price.lower() == "free",
                "genre": "",  # optional: extend scraper if genre info available
                "thumbnail_url": thumbnail_url,
                "thumbnail_path": thumbnail_path,
                "scrape_date": date.today().isoformat(),
                "listing_type": listing_type,
                "source_page": f"{listing_type}_page_{page}"
            })

        # next page
        next_btn = soup.select_one("a.next, a.next_page")
        url = "https://itch.io" + next_btn["href"] if next_btn and next_btn.has_attr("href") else None
        page += 1
    return results

def main():
    all_results = []
    for url, listing_type in [(POPULAR_URL, "popular"), (TOP_SELLERS_URL, "top_sellers")]:
        all_results += scrape_page(url, listing_type)

    df = pd.DataFrame(all_results)
    df.to_csv(CSV_FILE, index=False)
    print(f"Saved {len(all_results)} games to {CSV_FILE}")

if __name__ == "__main__":
    main()
