import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import date

# ------------------------
# Configuration
# ------------------------
BASE_URL = "https://itch.io"
DATA_DIR = "data"
THUMB_DIR = os.path.join(DATA_DIR, "thumbnails")

LISTINGS = {
    "popular": "https://itch.io/games/popular",
    "top_sellers": "https://itch.io/games/top-sellers",
}

PAGES_PER_LISTING = 2  # number of pages to scrape per listing

# ------------------------
# Thumbnail downloader
# ------------------------
def download_thumbnail(thumbnail_url, title, scrape_date):
    if not thumbnail_url:
        return None

    os.makedirs(THUMB_DIR, exist_ok=True)

    safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", title)[:50]
    ext = thumbnail_url.split(".")[-1].split("?")[0]
    filename = f"{scrape_date}_{safe_title}.{ext}"
    filepath = os.path.join(THUMB_DIR, filename)

    try:
        r = requests.get(thumbnail_url, timeout=10)
        if r.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(r.content)
            return filepath
    except Exception as e:
        print(f"Thumbnail failed for {title}: {e}")

    return None

# ------------------------
# Price helpers
# ------------------------
def parse_price(price_text):
    if not price_text:
        return None, None, True

    text = price_text.lower()

    if "free" in text:
        return "Free", None, True

    currency_match = re.search(r"[£$€]", price_text)
    currency = currency_match.group(0) if currency_match else None

    return price_text.strip(), currency, False

# ------------------------
# Scrape one listing page
# ------------------------
def scrape_listing_page(url, listing_type, page_num, scrape_date):
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")

    games = []

    for item in soup.select(".game_cell"):
        title_tag = item.select_one(".game_title")
        link_tag = item.select_one("a.game_link")

        if not title_tag or not link_tag:
            continue

        title = title_tag.text.strip()
        game_url = urljoin(BASE_URL, link_tag["href"])

        author_tag = item.select_one(".game_author")
        author = author_tag.text.strip() if author_tag else None

        price_tag = item.select_one(".price")
        price_text = price_tag.text.strip() if price_tag else None
        price, currency, is_free = parse_price(price_text)

        thumb_img = item.select_one(".game_thumb img")
        thumbnail_url = (
            urljoin(BASE_URL, thumb_img["src"])
            if thumb_img and thumb_img.get("src")
            else None
        )

        thumbnail_path = download_thumbnail(thumbnail_url, title, scrape_date)

        games.append({
            "scrape_date": scrape_date,
            "listing_type": listing_type,
            "source_page": f"{listing_type}_page_{page_num}",
            "title": title,
            "url": game_url,
            "author": author,
            "price": price,
            "currency": currency,
            "is_free": is_free,
            "thumbnail_url": thumbnail_url,
            "thumbnail_path": thumbnail_path,
        })

    return games

# ------------------------
# Main scraper runner
# ------------------------
def run_scraper():
    scrape_date = str(date.today())
    os.makedirs(DATA_DIR, exist_ok=True)

    combined_csv = os.path.join(DATA_DIR, "combined.csv")
    all_games = []

    for listing_type, base_url in LISTINGS.items():
        for page in range(1, PAGES_PER_LISTING + 1):
            url = f"{base_url}?page={page}"
            print(f"Scraping {url}")
            all_games.extend(
                scrape_listing_page(url, listing_type, page, scrape_date)
            )

    new_df = pd.DataFrame(all_games)

    if os.path.exists(combined_csv):
        old_df = pd.read_csv(combined_csv)
        new_df = pd.concat([old_df, new_df], ignore_index=True)

    new_df.to_csv(combined_csv, index=False)
    print(f"Scrape complete — {len(all_games)} new games added")

# ------------------------
# Entry point
# ------------------------
if __name__ == "__main__":
    run_scraper()
