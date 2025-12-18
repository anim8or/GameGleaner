# GameGleaner
# A Python script to scrape game data from Itch.io, including titles, URLs, authors, prices, and thumbnails.

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
from urllib.parse import urljoin
from datetime import date

# Base URL for Itch.io, used for constructing absolute URLs from relative paths.
BASE_URL = "https://itch.io"


def download_thumbnail(thumbnail_url: str, title: str, scrape_date: str) -> str | None:
    """
    Downloads a thumbnail image from a given URL and saves it to a local directory.

    Args:
        thumbnail_url (str): The URL of the thumbnail image to download.
        title (str): The title of the game, used to create a safe filename.
        scrape_date (str): The date of the scrape, used to prefix the filename for organization.

    Returns:
        str | None: The local file path of the downloaded thumbnail if successful,
                    otherwise None.
    """
    if not thumbnail_url:
        return None

    # Define the directory for saving thumbnails and create it if it doesn't exist.
    thumb_dir = os.path.join("data", "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)

    # Sanitize the title to create a valid filename.
    # Replaces non-alphanumeric characters with underscores and truncates to 50 characters.
    safe_title = re.sub(r"[^a-zA-Z0-9_-]", "_", title)[:50]
    # Extract the file extension from the URL, handling potential query parameters.
    ext = thumbnail_url.split(".")[-1].split("?")[0]
    # Construct the full filename.
    filename = f"{scrape_date}_{safe_title}.{ext}"
    filepath = os.path.join(thumb_dir, filename)

    try:
        # Send a GET request to download the thumbnail, with a 10-second timeout.
        r = requests.get(thumbnail_url, timeout=10)
        # Check if the request was successful (status code 200).
        if r.status_code == 200:
            # Write the content of the response (image data) to the file.
            with open(filepath, "wb") as f:
                f.write(r.content)
            return filepath
        else:
            print(f"Failed to download thumbnail for {title}: Status code {r.status_code}")
    except requests.exceptions.RequestException as e:
        # Catch specific request exceptions for better error handling.
        print(f"Failed to download thumbnail for {title} (Request Error): {e}")
    except Exception as e:
        # Catch any other unexpected errors during download.
        print(f"Failed to download thumbnail for {title} (General Error): {e}")
    return None


def scrape_listing_page(url: str, scrape_date: str) -> list[dict]:
    """
    Scrapes a single listing page on Itch.io to extract game details.

    Args:
        url (str): The URL of the Itch.io listing page (e.g., top sellers, popular).
        scrape_date (str): The date of the scrape, used for thumbnail filenames.

    Returns:
        list[dict]: A list of dictionaries, where each dictionary contains
                    details for one game found on the page.
    """
    print(f"Scraping: {url}")
    try:
        response = requests.get(url, timeout=15) # Add timeout for robustness
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    games = []
    # Select all game cells on the page.
    items = soup.select(".game_cell")
    for item in items:
        game_data = {}

        # Extract game title.
        title_element = item.select_one(".game_title a")
        game_data["title"] = title_element.text.strip() if title_element else "N/A"

        # Extract game URL.
        game_url_relative = title_element["href"] if title_element and "href" in title_element.attrs else ""
        game_data["url"] = urljoin(BASE_URL, game_url_relative) if game_url_relative else "N/A"

        # Extract author/developer name.
        author_element = item.select_one(".game_author a")
        game_data["author"] = author_element.text.strip() if author_element else "N/A"

        # Extract game price.
        price_element = item.select_one(".price")
        game_data["price"] = price_element.text.strip() if price_element else "Free" # Default to 'Free' if no price found

        # Extract thumbnail URL and download it.
        thumbnail_element = item.select_one(".game_thumb img")
        thumbnail_url = thumbnail_element["data-lazy_src"] if thumbnail_element and "data-lazy_src" in thumbnail_element.attrs else (
            thumbnail_element["src"] if thumbnail_element and "src" in thumbnail_element.attrs else None
        )
        game_data["thumbnail_path"] = download_thumbnail(thumbnail_url, game_data["title"], scrape_date)

        # Add the scrape date to the record.
        game_data["scrape_date"] = scrape_date

        games.append(game_data)
    return games


def run_scraper():
    """
    Orchestrates the entire scraping process.
    It fetches data from multiple Itch.io listing pages, processes it,
    downloads thumbnails, and saves the combined data to a CSV file.
    """
    # Get today's date to use for folder naming and data timestamping.
    scrape_date = str(date.today())
    # Create the base 'data' directory if it doesn't exist.
    os.makedirs("data", exist_ok=True)
    # Define the path for the combined CSV file.
    combined_csv_path = os.path.join("data", "combined.csv")

    all_games = []

    # Define the pages to scrape with their respective labels and URLs.
    pages = {
        "Top Sellers": "https://itch.io/games/top-sellers",
        "Popular": "https://itch.io/games/popular"
    }

    # Iterate through each defined category and multiple pages within each category.
    for label, page_url in pages.items():
        print(f"--- Scraping {label} games ---")
        # Scrape the first 2 pages for each category.
        for page in range(1, 3):
            # Construct the URL for the specific page number.
            url = f"{page_url}?page={page}"
            # Extend the overall list of games with results from the current page.
            all_games.extend(scrape_listing_page(url, scrape_date))

    # Convert the list of game dictionaries into a Pandas DataFrame.
    df = pd.DataFrame(all_games)

    # Handle appending to an existing combined CSV file to avoid duplicates.
    if os.path.exists(combined_csv_path):
        # Read the existing data.
        old_df = pd.read_csv(combined_csv_path)
        # Concatenate new data with old data.
        # Use `drop_duplicates` based on a combination of title and URL to prevent adding the same game multiple times
        # across different scrapes, assuming title+url uniquely identifies a game.
        df = pd.concat([old_df, df], ignore_index=True).drop_duplicates(subset=["title", "url"], keep="first")
        print(f"Appended new data to existing {combined_csv_path}. Total records: {len(df)}")
    else:
        print(f"Created new {combined_csv_path}. Total records: {len(df)}")

    # Save the DataFrame to a CSV file.
    df.to_csv(combined_csv_path, index=False)
    print("Scrape complete. Data saved to data/combined.csv")


if __name__ == "__main__":
    # This block ensures that `run_scraper()` is called only when the script is executed directly,
    # not when it's imported as a module into another script.
    run_scraper()
