from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import csv
import os
from pathlib import Path
import time
from urllib.parse import urljoin
from datetime import datetime

def load_config():
    """Load configuration with hardcoded defaults."""
    return {
        'scraper': {
            'base_url': 'https://www.trueup.io/locations',
            'output_path': 'data/trueup_locations.csv',
            'delay': 2,
            'max_locations': 0
        }
    }

def setup_driver():
    """Setup Selenium Chrome driver with options."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Use webdriver-manager to automatically download the correct ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def scrape_locations(base_url, delay=2):
    """Scrape location data from TrueUp locations page using Selenium."""
    print(f"Fetching: {base_url}")
    
    driver = setup_driver()
    locations = []
    
    try:
        driver.get(base_url)
        
        # Wait for page to load and Cloudflare to pass
        print("Waiting for page to load...")
        time.sleep(delay + 3)  # Extra time for Cloudflare
        
        # Wait for location links to be present
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all location links
        location_links = soup.find_all('a', href=lambda x: x and '/location/' in x)
        
        # Remove duplicates while preserving order
        seen_urls = set()
        unique_links = []
        for link in location_links:
            url = link.get('href')
            if url not in seen_urls:
                seen_urls.add(url)
                unique_links.append(link)
        
        for idx, link in enumerate(unique_links, 1):
            city_name = link.get_text(strip=True)
            city_url = urljoin(base_url, link['href'])
            
            locations.append({
                'rank': idx,
                'city': city_name,
                'url': city_url
            })
            
            print(f"Found: {city_name} - {city_url}")
        
    finally:
        driver.quit()
    
    return locations

def save_to_csv(data, output_path):
    """Save location data to CSV file."""
    # Add timestamp to filename
    timestamp = datetime.now().strftime('%Y-%m')
    base_path = Path(output_path)
    output_path_with_timestamp = base_path.parent / f"{base_path.stem}_{timestamp}{base_path.suffix}"
    
    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path_with_timestamp), exist_ok=True)
    
    with open(output_path_with_timestamp, 'w', newline='', encoding='utf-8') as f:
        if data:
            writer = csv.DictWriter(f, fieldnames=['rank', 'city', 'url'])
            writer.writeheader()
            writer.writerows(data)
    
    print(f"\nData saved to: {output_path_with_timestamp}")
    print(f"Total locations: {len(data)}")

def main():
    """Main execution function."""
    # Load configuration
    config = load_config()
    
    base_url = config['scraper']['base_url']
    output_path = config['scraper']['output_path']
    delay = config['scraper'].get('delay', 2)
    
    print("Starting TrueUp Locations Scraper...")
    print("=" * 50)
    
    try:
        # Scrape locations
        locations = scrape_locations(base_url, delay)
        
        if not locations:
            print("Warning: No locations found. The page structure may have changed.")
        
        # Save to CSV
        save_to_csv(locations, output_path)
        
        print("\nScraping completed successfully!")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
