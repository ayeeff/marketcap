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
from datetime import datetime

# Configuration
BASE_URL = "https://www.marketcapwatch.com"
COUNTRIES_URL = f"{BASE_URL}/all-countries/"
REPO_NAME = "ayeeff/marketcap"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Empire definitions
EMPIRE_1_COUNTRIES = [
    'United Kingdom', 'UK', 'Great Britain',
    'Canada', 'Australia', 'Singapore',
    'New Zealand', 'South Africa', 'Malaysia',
    'Nigeria', 'Kenya', 'Ghana', 'Jamaica',
    'Uganda', 'Tanzania', 'Zambia', 'Malawi',
    'Cyprus', 'Malta', 'Mauritius', 'Botswana',
    'Namibia', 'Zimbabwe', 'Barbados',
    'Trinidad and Tobago', 'Fiji', 'Papua New Guinea'
]

EMPIRE_2_COUNTRIES = ['United States', 'United States of America', 'USA']

EMPIRE_3_COUNTRIES = ['China', 'Hong Kong', 'Taiwan']

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def parse_market_cap(value):
    if pd.isna(value) or value == '' or value == '-':
        return 0
    value = str(value).replace('$', '').replace(',', '').replace(' ', '').strip()
    multiplier = 1
    if 'T' in value.upper():
        multiplier = 1_000_000_000_000
        value = value.upper().replace('T', '').strip()
    elif 'B' in value.upper():
        multiplier = 1_000_000_000
        value = value.upper().replace('B', '').strip()
    elif 'M' in value.upper():
        multiplier = 1_000_000
        value = value.upper().replace('M', '').strip()
    try:
        return float(value) * multiplier
    except (ValueError, AttributeError):
        return 0

def format_market_cap(value):
    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f} T"
    elif value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f} B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.2f} M"
    return f"${value:.2f}"

def scrape_countries_data(driver):
    print(f"Loading page: {COUNTRIES_URL}")
    driver.get(COUNTRIES_URL)
    time.sleep(5)
    
    tables = driver.find_elements(By.TAG_NAME, "table")
    if not tables:
        raise ValueError("No tables found on page")
    
    table = tables[0]
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    
    for row in rows:
        cells_th = row.find_elements(By.TAG_NAME, "th")
        cells_td = row.find_elements(By.TAG_NAME, "td")
        all_cells = cells_th + cells_td
        cells = [cell.text.strip() for cell in all_cells]
        if cells and any(cell for cell in cells):
            data.append(cells)
    
    if not data:
        raise ValueError("No data extracted from table")
    
    columns = data[0]
    df = pd.DataFrame(data[1:], columns=columns)
    
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].apply(lambda x: str(x).replace(',', '') if isinstance(x, str) and any(c.isdigit() for c in str(x)) else x)
    
    print(f"✓ Extracted {len(df)} countries")
    return df

def get_country_slug(country_name):
    import re
    country_lower = country_name.lower().strip()
    if country_lower == 'hong kong':
        return 'hongkong'
    slug = country_lower.replace(' ', '-').replace('&', 'and')
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    return slug

def scrape_top_companies(driver, country_name):
    country_slug = get_country_slug(country_name)
    url = f"{BASE_URL}/{country_slug}/largest-companies-in-{country_slug}/"
    
    print(f"  Scraping {country_name} companies from {url}")
    try:
        driver.get(url)
        time.sleep(3)
        tables = driver.find_elements(By.TAG_NAME, "table")
        if not tables:
            print(f"  ⚠️ No table found for {country_name}")
            return []
        table = tables[0]
        rows = table.find_elements(By.TAG_NAME, "tr")
        companies = []
        for idx, row in enumerate(rows[1:11]):  # Top 10
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 3:
                try:
                    company_name = cells[1].text.strip()
                    market_cap = cells[2].text.strip()
                    logo_url = ""
                    try:
                        img_element = cells[1].find_element(By.TAG_NAME, "img")
                        logo_url = img_element.get_attribute("src")
                    except:
                        pass
                    companies.append({
                        'Company': company_name,
                        'Logo': logo_url,
                        'Market Cap': market_cap
                    })
                except Exception as e:
                    print(f"  ⚠️ Error parsing row {idx}: {e}")
        print(f"  ✓ Found {len(companies)} companies")
        return companies
    except Exception as e:
        print(f"  ❌ Error scraping {country_name}: {e}")
        return []

def main():
    print("="*80)
    print("EMPIRE MARKET CAP SCRAPER")
    print("="*80)
    
    os.makedirs('data', exist_ok=True)
    
    driver = setup_driver()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    
    try:
        # Scrape all countries data
        df_countries = scrape_countries_data(driver)
        
        market_cap_col = None
        country_col = None
        for col in df_countries.columns:
            if 'market' in col.lower() and 'cap' in col.lower():
                market_cap_col = col
            if 'country' in col.lower():
                country_col = col
        if not market_cap_col or not country_col:
            raise ValueError(f"Required columns not found. Available: {list(df_countries.columns)}")
        
        df_countries['MarketCapNumeric'] = df_countries[market_cap_col].apply(parse_market_cap)
        df_countries['CountryNormalized'] = df_countries[country_col].str.strip().str.lower()
        
        # Calculate empire totals
        print("\n" + "="*80)
        print("CALCULATING EMPIRE TOTALS")
        print("="*80)
        
        empire_data = []
        
        # Empire 1
        empire_1_normalized = [c.strip().lower() for c in EMPIRE_1_COUNTRIES]
        empire_1_df = df_countries[df_countries['CountryNormalized'].isin(empire_1_normalized)]
        empire_1_total = empire_1_df['MarketCapNumeric'].sum()
        print(f"\nEmpire 1 (Commonwealth): {format_market_cap(empire_1_total)}")
        print(f"  Countries found: {len(empire_1_df)}")
        empire_data.append({'Empire': 1, 'Total Market Cap': format_market_cap(empire_1_total), 'Date': today})
        
        # Empire 2
        empire_2_normalized = [c.strip().lower() for c in EMPIRE_2_COUNTRIES]
        empire_2_df = df_countries[df_countries['CountryNormalized'].isin(empire_2_normalized)]
        empire_2_total = empire_2_df['MarketCapNumeric'].sum()
        print(f"\nEmpire 2 (USA): {format_market_cap(empire_2_total)}")
        print(f"  Countries found: {len(empire_2_df)}")
        empire_data.append({'Empire': 2, 'Total Market Cap': format_market_cap(empire_2_total), 'Date': today})
        
        # Empire 3
        empire_3_normalized = [c.strip().lower() for c in EMPIRE_3_COUNTRIES]
        empire_3_df = df_countries[df_countries['CountryNormalized'].isin(empire_3_normalized)]
        empire_3_total = empire_3_df['MarketCapNumeric'].sum()
        print(f"\nEmpire 3 (China+HK+TW): {format_market_cap(empire_3_total)}")
        print(f"  Countries found: {len(empire_3_df)}")
        empire_data.append({'Empire': 3, 'Total Market Cap': format_market_cap(empire_3_total), 'Date': today})
        
        # Save empire totals CSV
        df_empire_totals = pd.DataFrame(empire_data)
        empire_totals_file = 'data/empire_totals.csv'
        df_empire_totals.to_csv(empire_totals_file, index=False)
        print(f"\n✓ Saved empire totals to {empire_totals_file}")
        
        # Scrape top 10 companies for each empire
        print("\n" + "="*80)
        print("SCRAPING TOP COMPANIES FOR EACH EMPIRE")
        print("="*80)
        
        all_companies = []

        def scrape_empire_companies(empire_df, empire_num, empire_name):
            print(f"\n[Empire {empire_num}: {empire_name}]")
            for _, row in empire_df.iterrows():
                country = row[country_col]
                companies = scrape_top_companies(driver, country)
                for company in companies:
                    company['Empire'] = empire_num
                    company['Country'] = country  # Add country of origin
                    all_companies.append(company)
                time.sleep(1)
        
        scrape_empire_companies(empire_1_df, 1, "Commonwealth")
        scrape_empire_companies(empire_2_df, 2, "USA")
        scrape_empire_companies(empire_3_df, 3, "China+HK+TW")
        
        df_all_companies = pd.DataFrame(all_companies)
        
        if len(df_all_companies) > 0:
            df_all_companies['MarketCapNumeric'] = df_all_companies['Market Cap'].apply(parse_market_cap)
            
            # Top 10 per empire
            top_companies = []
            for empire_num in [1, 2, 3]:
                empire_companies = df_all_companies[df_all_companies['Empire'] == empire_num]
                top_10 = empire_companies.nlargest(10, 'MarketCapNumeric')
                top_companies.append(top_10)
            
            df_top_companies = pd.concat(top_companies, ignore_index=True)
            df_top_companies = df_top_companies[['Empire', 'Company', 'Country', 'Logo', 'Market Cap']]
            
            companies_file = 'data/empire_top_companies.csv'
            df_top_companies.to_csv(companies_file, index=False)
            print(f"\n✓ Saved top companies to {companies_file}")
            print(f"  Total companies: {len(df_top_companies)}")
        else:
            print("\n⚠️ No companies data collected")
        
        # Upload to GitHub
        if GITHUB_TOKEN:
            print("\n" + "="*80)
            print("UPLOADING TO GITHUB")
            print("="*80)
            auth = Auth.Token(GITHUB_TOKEN)
            g = Github(auth=auth)
            repo = g.get_repo(REPO_NAME)
            timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
            
            files_to_upload = [
                ('data/empire_totals.csv', empire_totals_file),
                ('data/empire_top_companies.csv', companies_file)
            ]
            
            for github_path, local_path in files_to_upload:
                if os.path.exists(local_path):
                    with open(local_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    commit_msg = f"Update {os.path.basename(github_path)} - {timestamp}"
                    try:
                        file_obj = repo.get_contents(github_path)
                        repo.update_file(github_path, commit_msg, content, file_obj.sha)
                        print(f"✓ Updated {github_path}")
                    except:
                        repo.create_file(github_path, commit_msg, content)
                        print(f"✓ Created {github_path}")
                    os.remove(local_path)
            print("\n✅ All files uploaded successfully!")
        else:
            print("\n⚠️ No GitHub token found, skipping upload")
        
        print("\n" + "="*80)
        print("✅ SCRAPING COMPLETED SUCCESSFULLY!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        driver.quit()
        print("\n✓ Driver closed")

if __name__ == "__main__":
    main()
