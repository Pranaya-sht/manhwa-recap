
import sys
import logging
from app.scraper import ManhwaScraper

logging.basicConfig(level=logging.INFO)

def test_scrape():
    url = "https://asuracomic.net/series/the-extras-academy-survival-guide-c8fdcde7/chapter/83"
    print(f"Testing scraper with URL: {url}")
    
    scraper = ManhwaScraper("temp_test_output")
    try:
        result = scraper.scrape(url)
        print("Scraping successful!")
        print(f"Images found: {result['image_count']}")
    except Exception as e:
        print(f"Scraping failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_scrape()
