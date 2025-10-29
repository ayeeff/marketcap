import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import yaml
import logging
from typing import List, Dict, Optional
import re

class ChinaInvestmentTrackerScraper:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the scraper with configuration."""
        self.load_config(config_path)
        self.setup_logging()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def load_config(self, config_path: str):
        """Load configuration from YAML file."""
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Create output directory if it doesn't exist
        os.makedirs(self.config['output_dir'], exist_ok=True)
    
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(self.config['output_dir'], 'scraping.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def clean_amount(self, amount_str: str) -> float:
        """Convert amount string to float."""
        if not amount_str or amount_str.strip() == '':
            return 0.0
        
        # Remove currency symbols, commas, and whitespace
        cleaned = re.sub(r'[^\d.]', '', amount_str.strip())
        
        try:
            return float(cleaned)
        except ValueError:
            self.logger.warning(f"Could not convert amount: {amount_str}")
            return 0.0
    
    def extract_table_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract data from the HTML table."""
        data = []
        
        # Find the table - you might need to adjust this selector
        table = soup.find('table')
        if not table:
            self.logger.error("No table found on the page")
            return data
        
        # Find all rows in the table body
        rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 7:  # Ensure we have enough columns
                try:
                    record = {
                        'yr': cells[0].get_text(strip=True),
                        'month': cells[1].get_text(strip=True),
                        'investor_or_builder': cells[2].get_text(strip=True),
                        'sector': cells[3].get_text(strip=True),
                        'country': cells[4].get_text(strip=True),
                        'amount': self.clean_amount(cells[5].get_text(strip=True)),
                        'type': cells[6].get_text(strip=True)
                    }
                    data.append(record)
                except Exception as e:
                    self.logger.error(f"Error processing row: {e}")
                    continue
        
        return data
    
    def scrape_all_data(self) -> List[Dict]:
        """Scrape all data from the website with pagination."""
        all_data = []
        page = 1
        
        while True:
            self.logger.info(f"Scraping page {page}")
            
            # Construct URL with pagination parameters
            if page == 1:
                url = self.config['base_url']
            else:
                url = f"{self.config['base_url']}?start={((page-1)*100)}"
            
            try:
                response = self.session.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_data = self.extract_table_data(soup)
                
                if not page_data:
                    self.logger.info("No more data found")
                    break
                
                all_data.extend(page_data)
                self.logger.info(f"Extracted {len(page_data)} records from page {page}")
                
                # Check if there's a next page
                next_link = soup.find('a', string=re.compile(r'next|>', re.I))
                if not next_link:
                    self.logger.info("No next page found")
                    break
                
                page += 1
                time.sleep(self.config['wait_time'])
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching page {page}: {e}")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error on page {page}: {e}")
                break
        
        return all_data
    
    def save_to_csv(self, data: List[Dict]):
        """Save data to CSV file."""
        output_path = os.path.join(
            self.config['output_dir'], 
            self.config['output_filename']
        )
        
        df = pd.DataFrame(data)
        df.to_csv(output_path, index=False)
        self.logger.info(f"Data saved to {output_path}")
        self.logger.info(f"Total records: {len(data)}")
        
        # Print summary statistics
        if not df.empty:
            self.logger.info(f"Date range: {df['yr'].min()} - {df['yr'].max()}")
            self.logger.info(f"Total amount: ${df['amount'].sum():,.2f}")
            self.logger.info(f"Unique countries: {df['country'].nunique()}")
    
    def run(self):
        """Main method to run the scraper."""
        self.logger.info("Starting China Global Investment Tracker scraper")
        
        try:
            data = self.scrape_all_data()
            
            if data:
                self.save_to_csv(data)
                self.logger.info("Scraping completed successfully")
            else:
                self.logger.warning("No data was scraped")
                
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}")

def main():
    """Main function."""
    scraper = ChinaInvestmentTrackerScraper()
    scraper.run()

if __name__ == "__main__":
    main()
