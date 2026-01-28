"""
Web Scraper Module for Manhwa Chapters
Supports multiple manhwa websites with auto-detection
"""

import os
import re
import time
import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from io import BytesIO
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManhwaScraper:
    """Scraper for extracting images from manhwa chapter URLs"""
    
    # Known website patterns and their selectors
    SITE_CONFIGS = {
        'asura': {
            'patterns': ['asura', 'asuratoon', 'asurascans', 'asuratoon.com', 'asuracomic'],
            'img_selector': 'div.rdminimal img, div.reading-content img, img.wp-manga-chapter-img, div.w-full.mx-auto.center img, img[alt*="chapter page"]',
            'use_selenium': True
        },
        'reaper': {
            'patterns': ['reaper', 'reaperscans'],
            'img_selector': 'div.reading-content img, p img',
            'use_selenium': True
        },
        'flame': {
            'patterns': ['flame', 'flamescans', 'flamecomics'],
            'img_selector': 'div.reading-content img, div#readerarea img',
            'use_selenium': True
        },
        'mangadex': {
            'patterns': ['mangadex'],
            'img_selector': 'img.page',
            'use_selenium': True
        },
        'webtoon': {
            'patterns': ['webtoon', 'webtoons'],
            'img_selector': 'div._imageViewer img',
            'use_selenium': True
        },
        'generic': {
            'patterns': [],
            'img_selector': 'img',
            'use_selenium': True
        }
    }
    
    def __init__(self, output_dir: str = "temp"):
        self.output_dir = output_dir
        self.driver = None
        
    def _detect_site(self, url: str) -> dict:
        """Detect which manhwa site the URL belongs to"""
        domain = urlparse(url).netloc.lower()
        
        for site_name, config in self.SITE_CONFIGS.items():
            for pattern in config['patterns']:
                if pattern in domain:
                    logger.info(f"Detected site: {site_name}")
                    return config
        
        logger.info("Using generic scraper configuration")
        return self.SITE_CONFIGS['generic']
    
    def _setup_driver(self):
        """Setup Selenium WebDriver with Chrome"""
        if self.driver:
            return
            
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Optimization: Don't wait for all resources to load
        options.page_load_strategy = 'eager'
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(60)  # 60 seconds timeout
            self.driver.set_script_timeout(60)
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def _close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _extract_manga_info(self, url: str) -> dict:
        """Extract manga name and chapter number from URL"""
        # Common URL patterns
        patterns = [
            r'/(?:manga|comic|series)/([^/]+)/chapter[/-]?(\d+)',
            r'/([^/]+)/chapter[/-]?(\d+)',
            r'/([^/]+)-chapter-(\d+)',
            r'/chapter/([^/]+)/(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                manga_name = match.group(1).replace('-', ' ').replace('_', ' ').title()
                chapter_num = match.group(2)
                return {'manga_name': manga_name, 'chapter': chapter_num}
        
        # Fallback: extract from URL path
        path = urlparse(url).path
        parts = [p for p in path.split('/') if p]
        
        return {
            'manga_name': parts[0] if parts else 'Unknown',
            'chapter': parts[-1] if len(parts) > 1 else '1'
        }
    
    def _download_image(self, img_url: str, save_path: str, retry_count: int = 3) -> bool:
        """Download an image with retry mechanism"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': urlparse(img_url).scheme + '://' + urlparse(img_url).netloc
        }
        
        for attempt in range(retry_count):
            try:
                response = requests.get(img_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                # Convert to standard format
                img = Image.open(BytesIO(response.content))
                
                # Convert RGBA to RGB if needed
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                img.save(save_path, 'JPEG', quality=95)
                return True
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {img_url}: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2)
        
        return False
    
    def _scrape_with_selenium(self, url: str, config: dict) -> list:
        """Scrape images using Selenium for JavaScript-rendered pages"""
        self._setup_driver()
        
        try:
            logger.info(f"Loading page with Selenium: {url}")
            self.driver.get(url)
            
            # Wait for images to load (Explicit wait for any of the selectors)
            try:
                # Use the full selector string which works with CSS_SELECTOR
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, config['img_selector']))
                )
                logger.info("Found initial images, proceeding...")
            except Exception:
                logger.warning(f"Wait for images timed out, proceeding with scroll explicitly...")

            time.sleep(2)
            
            # Scroll to load lazy-loaded images
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Find all image elements
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Try multiple selectors
            selectors = config['img_selector'].split(', ')
            images = []
            
            for selector in selectors:
                found = soup.select(selector)
                images.extend(found)
            
            # Extract image URLs
            img_urls = []
            for img in images:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    # Make absolute URL
                    if not src.startswith('http'):
                        src = urljoin(url, src)
                    
                    # Filter out icons, logos, etc.
                    if self._is_valid_manga_image(src):
                        img_urls.append(src)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for u in img_urls:
                if u not in seen:
                    seen.add(u)
                    unique_urls.append(u)
            
            if not unique_urls:
                raise ValueError("No images found on the page")

            return unique_urls
            
        except Exception as e:
            if "TimeoutException" in str(e) or "timed out" in str(e).lower():
                logger.warning(f"Page load timed out, but continuing... (Error: {e})")
                # Try to proceed anyway if we got some images, or allow retry logic to handle it
                # For now, just re-raising but catching specific timeout helps validation
            logger.error(f"Selenium scraping failed: {e}")
            raise
    
    def _scrape_with_bs4(self, url: str, config: dict) -> list:
        """Scrape images using BeautifulSoup for static pages"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try multiple selectors
            selectors = config['img_selector'].split(', ')
            images = []
            
            for selector in selectors:
                found = soup.select(selector)
                images.extend(found)
            
            img_urls = []
            for img in images:
                src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if src:
                    if not src.startswith('http'):
                        src = urljoin(url, src)
                    
                    if self._is_valid_manga_image(src):
                        img_urls.append(src)
            
            # Remove duplicates
            return list(dict.fromkeys(img_urls))
            
        except Exception as e:
            logger.error(f"BS4 scraping failed: {e}")
            raise
    
    def _is_valid_manga_image(self, url: str) -> bool:
        """Check if URL is likely a manga panel image"""
        url_lower = url.lower()
        
        # Skip common non-manga images
        skip_patterns = [
            'logo', 'icon', 'avatar', 'banner', 'button',
            'advertisement', 'ad.', 'ads.', 'tracking',
            'facebook', 'twitter', 'discord', 'google',
            'favicon', 'loading', 'spinner'
        ]
        
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        
        # Check for valid image extensions
        valid_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        has_valid_ext = any(ext in url_lower for ext in valid_extensions)
        
        return has_valid_ext
    
    def scrape(self, url: str, progress_callback=None) -> dict:
        """
        Main scraping method
        Returns: dict with 'images_dir', 'manga_info', 'image_count'
        """
        try:
            # Detect site configuration
            config = self._detect_site(url)
            
            # Extract manga info
            manga_info = self._extract_manga_info(url)
            logger.info(f"Manga: {manga_info['manga_name']}, Chapter: {manga_info['chapter']}")
            
            # Create output directory
            safe_name = re.sub(r'[^\w\s-]', '', manga_info['manga_name']).strip()
            images_dir = os.path.join(
                self.output_dir,
                safe_name,
                f"chapter_{manga_info['chapter']}",
                "images"
            )
            os.makedirs(images_dir, exist_ok=True)
            
            # Scrape image URLs
            if config['use_selenium']:
                img_urls = self._scrape_with_selenium(url, config)
            else:
                img_urls = self._scrape_with_bs4(url, config)
            
            if not img_urls:
                raise ValueError("No images found on the page")
            
            logger.info(f"Found {len(img_urls)} images")
            
            # Download images
            downloaded = 0
            for idx, img_url in enumerate(img_urls):
                filename = f"panel_{idx+1:03d}.jpg"
                save_path = os.path.join(images_dir, filename)
                
                if self._download_image(img_url, save_path):
                    downloaded += 1
                    logger.info(f"Downloaded: {filename}")
                else:
                    logger.warning(f"Failed to download: {img_url}")
                
                if progress_callback:
                    progress_callback(idx + 1, len(img_urls))
            
            logger.info(f"Successfully downloaded {downloaded}/{len(img_urls)} images")
            
            return {
                'images_dir': images_dir,
                'manga_info': manga_info,
                'image_count': downloaded,
                'total_found': len(img_urls)
            }
            
        finally:
            self._close_driver()


def scrape_chapter(url: str, output_dir: str = "temp", progress_callback=None) -> dict:
    """Convenience function for scraping a chapter"""
    scraper = ManhwaScraper(output_dir)
    return scraper.scrape(url, progress_callback)


if __name__ == "__main__":
    # Test with a sample URL
    import sys
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        result = scrape_chapter(test_url)
        print(f"\nScraping complete!")
        print(f"Images saved to: {result['images_dir']}")
        print(f"Downloaded: {result['image_count']} images")
