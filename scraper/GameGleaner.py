import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime
from urllib.parse import urljoin

# ----------------------------
# CONFIGURATION
# ----------------------------
POPULAR_URL = "https://itch.io/games/popular"
TOP_SELLERS_URL = "https://itch.io/games/top-sellers"
DATA_DIR = "data"
THUMB_DIR = os.path.join(DATA_DIR, "thumbnails")
os.makedirs(THUMB_DIR, exist_ok=True)
CSV_FILE = os.path.join(DATA_DIR, "itch_games.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ----------------------------
# HELPER FUNCTIONS
# ----------------------------
def download_thumbnail(url, title):
    """Download thumbnail to local folder, return path."""
    try:
        ext = url.split(".")[-1].split("?")[0]
        safe_title = "".join(c if c.isalnum() else "_" for c in title)
        path = os.path.join(THUMB_DIR, f"{datetime.today().strftime('%Y-%m-%d')}_{safe_title}.{ext}")
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except Exception as e:
        print(f"Failed to download thumbnail {url}: {e}")
    return ""

def parse_price(price_text):
    """Extract price, currency, and free status."""
    if not price_text:
        return "", "", True
    price_text = price_text.strip()
    if price_text.lower() == "free":
        return "0", "", True
    import re
    match = re.match(r"([^\d]*)([\d\.,]+)", price_text)
    if match:
        currency, price = match.groups()
        return price, currency.strip(), False
    return price_text, "", False

# ----------------------------
# SCRAPER
# ----------------------------
def scrape_page(url, listing_type="popular"):
    print(f"Scraping {listing_type} page: {url}")
    all_results = []
    page_num = 1
    while url:
        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        games = soup.select(".game_cell")
        for g in games:
            title_tag = g.select_one(".title > a")
            title = title_tag.get_text(strip=True) if title_tag else "Unknown"
            game_url = urljoin("https://itch.io", title_tag["href"]) if title_tag else ""
            author = g.select_one(".author").get_text(strip=True) if g.select_one(".author") else ""
            
            # Price
            price_tag = g.select_one(".price")
            price_text = price_tag.get_text(strip=True) if price_tag else "Free"
            price, currency, is_free = parse_price(price_text)
            
            # Genre (first one listed)
            genre_tag = g.select_one(".game_genre a")
            genre = genre_tag.get_text(strip=True) if genre_tag else ""
            
            # Thumbnail
            thumb_tag = g.select_one(".game_icon img")
            thumb_url = thumb_tag["src"] if thumb_tag else ""
            thumb_path = download_thumbnail(thumb_url, title) if thumb_url else ""
            
            all_results.append({
                "title": title,
                "url": game_url,
                "author": author,
                "price": price,
                "currency": currency,
                "is_free": is_free,
                "genre": genre,
                "thumbnail_url": thumb_url,
                "thumbnail_path": thumb_path,
                "scrape_date": datetime.today().strftime("%Y-%m-%d"),
                "listing_type": listing_type,
                "source_page": f"{listing_type}_page_{page_num}"
            })

        # Pagination
        next_btn = soup.select_one(".next_page")
        if next_btn and next_btn.has_attr("href"):
            url = urljoin("https://itch.io", next_btn["href"])
            page_num += 1
        else:
            url = None

    return all_results

# ----------------------------
# RUN SCRAPES
# ----------------------------
all_results = []
all_results += scrape_page(POPULAR_URL, "popular")
all_results += scrape_page(TOP_SELLERS_URL, "top_sellers")

# ----------------------------
# SAVE TO CSV
# ----------------------------
df = pd.DataFrame(all_results)
os.makedirs(DATA_DIR, exist_ok=True)
df.to_csv(CSV_FILE, index=False)
print(f"Saved {len(all_results)} records to {CSV_FILE}")
