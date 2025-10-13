import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from github import Github, Auth
import time
import re

# Configuration
BASE_URL = "https://www.marketcapwatch.com"
COUNTRIES_URL = f"{BASE_URL}/all-countries/"
TOP_N_COUNTRIES = 15
TOP_N_COMPANIES = 10
REPO_NAME = "ayeeff/marketcap"

# Load GitHub token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def setup_driver():
    """Setup Chrome driver with options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def get_country_url_slug(country_name):
    """Convert country name to URL slug"""
    slug = country_name.lower()
    slug = slug.replace(' ', '-')
    slug = slug.replace('&', 'and')
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    return slug

def scrape_top_companies(driver, country_name, country_url):
    """Scrape top companies for a given country"""
    print(f"\n  Scraping {country_name}...")
    
    try:
        driver.get(country_url)
        time.sleep(3)
        
        # Find the companies table
        wait = WebDriverWait(driver, 15)
        tables = driver.find_elements(By.TAG_NAME, "table")
        
        if not tables:
            print(f"  ⚠️ No table found for {country_name}")
            return None
        
        # Use first table (companies list)
        table = tables[0]
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        companies_data = []
        
        for idx, row in enumerate(rows[1:TOP_N_COMPANIES + 1]):  # Skip header, get top 10
            cells = row.find_elements(By.TAG_NAME, "td")
            
            if len(cells) >= 3:
                # Extract: Rank, Name, Market Cap
                try:
                    rank = cells[0].text.strip()
                    name = cells[1].text.strip()
                    market_cap = cells[2].text.strip()
                    
                    # Remove commas from rank if present
                    rank = rank.replace(',', '')
                    
                    companies_data.append({
                        'Rank': rank,
                        'Company': name,
                        'Market Cap': market_cap
                    })
                except Exception as e:
                    print(f"  ⚠️ Error parsing row {idx}: {e}")
                    continue
        
        if companies_data:
            print(f"  ✓ Extracted {len(companies_data)} companies from {country_name}")
            return pd.DataFrame(companies_data)
        else:
            print(f"  ⚠️ No company data extracted for {country_name}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error scraping {country_name}: {e}")
        return None

def main():
    print("="*80)
    print("COUNTRY COMPANIES SCRAPER - Top Companies by Country")
    print("="*80)
    
    # Read the countries CSV to get top 15
    countries_csv = "countries_marketcap.csv"
    
    if not os.path.exists(countries_csv):
        print(f"❌ {countries_csv} not found. Run main.py first!")
        return
    
    df_countries = pd.read_csv(countries_csv)
    
    # Find country column
    country_col = None
    for col in df_countries.columns:
        if 'country' in col.lower():
            country_col = col
            break
    
    if not country_col:
        print(f"❌ Could not find country column in {countries_csv}")
        return
    
    # Get top 15 countries
    top_countries = df_countries.head(TOP_N_COUNTRIES)
    
    print(f"\nTop {TOP_N_COUNTRIES} countries to scrape:")
    for idx, row in top_countries.iterrows():
        print(f"  {idx + 1}. {row[country_col]}")
    
    # Setup driver
    print("\nSetting up Chrome driver...")
    driver = setup_driver()
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    scraped_files = []
    
    try:
        for idx, row in top_countries.iterrows():
            country_name = row[country_col]
            
            # Generate URL
            country_slug = get_country_url_slug(country_name)
            country_url = f"{BASE_URL}/{country_slug}/largest-companies-in-{country_slug}/"
            
            print(f"\n[{idx + 1}/{TOP_N_COUNTRIES}] {country_name}")
            print(f"  URL: {country_url}")
            
            # Scrape companies
            df_companies = scrape_top_companies(driver, country_name, country_url)
            
            if df_companies is not None and len(df_companies) > 0:
                # Save to CSV
                filename = f"data/{country_slug}_top_companies.csv"
                df_companies.to_csv(filename, index=False)
                print(f"  ✓ Saved to {filename}")
                scraped_files.append(filename)
            else:
                print(f"  ⚠️ Skipping {country_name} - no data")
            
            # Small delay between requests
            time.sleep(2)
        
        print("\n" + "="*80)
        print(f"✓ Scraping complete! Created {len(scraped_files)} CSV files.")
        print("="*80)
        
        # Upload to GitHub if token available
        if GITHUB_TOKEN and scraped_files:
            print("\nUploading files to GitHub...")
            auth = Auth.Token(GITHUB_TOKEN)
            g = Github(auth=auth)
            repo = g.get_repo(REPO_NAME)
            
            timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M UTC')
            
            for filename in scraped_files:
                try:
                    with open(filename, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    github_path = filename  # Already has data/ prefix
                    commit_message = f"Update {os.path.basename(filename)} - {timestamp}"
                    
                    try:
                        file = repo.get_contents(github_path)
                        repo.update_file(github_path, commit_message, content, file.sha)
                        print(f"  ✓ Updated {github_path}")
                    except Exception as e:
                        if "not found" in str(e).lower() or "404" in str(e):
                            repo.create_file(github_path, commit_message, content)
                            print(f"  ✓ Created {github_path}")
                        else:
                            print(f"  ⚠️ Error with {github_path}: {e}")
                    
                    # Clean up local file
                    os.remove(filename)
                    
                except Exception as e:
                    print(f"  ❌ Failed to upload {filename}: {e}")
            
            print("\n✅ All files uploaded to GitHub!")
        else:
            print("\n⚠️ No GitHub token found or no files to upload")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("\n✓ Driver closed.")

if __name__ == "__main__":
    main()
