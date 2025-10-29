import requests
from bs4 import BeautifulSoup
import csv
import os
import yaml
from pathlib import Path
import time
from urllib.parse import urljoin
from datetime import datetime

def load_config(config_path='config.yml'):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def scrape_locations(base_url, delay=1):
    """Scrape location data from TrueUp locations page."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"Fetching: {base_url}")
    response = requests.get(base_url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    locations = []
    
    # Find all location links - adjust selectors based on actual HTML structure
    location_links = soup.find_all('a', href=lambda x: x and '/location/' in x)
    
    for idx, link in enumerate(location_links, 1):
        city_name = link.get_text(strip=True)
        city_url = urljoin(base_url, link['href'])
        
        locations.append({
            'rank': idx,
            'city': city_name,
            'url': city_url
        })
        
        print(f"Found: {city_name} - {city_url}")
    
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
    delay = config['scraper'].get('delay', 1)
    
    print("Starting TrueUp Locations Scraper...")
    print("=" * 50)
    
    try:
        # Scrape locations
        locations = scrape_locations(base_url, delay)
        
        # Save to CSV
        save_to_csv(locations, output_path)
        
        print("\nScraping completed successfully!")
        
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
