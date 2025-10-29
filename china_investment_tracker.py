import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from github import Github, Auth
import time

# Configuration
URL = "https://www.aei.org/china-global-investment-tracker/"
REPO_NAME = "ayeeff/marketcap"  # Adjust if needed for your repo
FILE_PATH = "data/china_investments.csv"

# Load token from environment variable (provided by GitHub Actions)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Only validate if running locally (not in CI)
if not GITHUB_TOKEN and not os.getenv("CI"):
    raise ValueError(
        "GITHUB_TOKEN environment variable not set.\n"
        "Run: export GITHUB_TOKEN=your_token_here"
    )

if GITHUB_TOKEN:
    print("✓ GitHub token loaded successfully.")

def setup_driver():
    """Setup Chrome driver with options."""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--remote-debugging-port=9222')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-plugins-discovery')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')

    print("Setting up ChromeDriver...")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def handle_cookies(driver, wait):
    """Handle cookie consent if present."""
    try:
        # XPATH selectors
        xpath_selectors = [
            "//button[contains(text(), 'Accept')]",
            "//button[contains(text(), 'Agree')]"
        ]
        # CSS selectors
        css_selectors = [
            "[data-testid='cookie-accept']",
            ".cookie-accept",
            "#cookie-accept"
        ]
        
        # Try XPATH first
        for selector in xpath_selectors:
            try:
                accept_btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                accept_btn.click()
                print("✓ Cookie consent accepted (XPath).")
                time.sleep(2)
                return
            except TimeoutException:
                continue
        
        # Try CSS
        for selector in css_selectors:
            try:
                accept_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                accept_btn.click()
                print("✓ Cookie consent accepted (CSS).")
                time.sleep(2)
                return
            except TimeoutException:
                continue
    except Exception as e:
        print(f"⚠️ No cookie banner found or error: {e}")

def wait_for_table(driver, wait, max_attempts=3):
    """Robust wait for the DataTable to load."""
    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt + 1}/{max_attempts} waiting for table...")
            # Try multiple selectors for the table
            table_selectors = [
                "table.dataTable",
                "table.table",
                ".dataTable",
                "table"
            ]
            table = None
            for sel in table_selectors:
                try:
                    table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                    print(f"✓ Table found with selector: {sel}")
                    break
                except TimeoutException:
                    continue
            
            if table is None:
                raise TimeoutException("No table found with any selector.")
            
            # Additional wait for rows to populate
            wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, f"{sel} tbody tr")) > 0)
            print("✓ Table loaded with data.")
            return table
        except TimeoutException:
            print(f"⚠️ Attempt {attempt + 1} timed out, retrying...")
            time.sleep(15)
            # Refresh page on retry
            if attempt > 0:
                driver.refresh()
                time.sleep(5)
                # Scroll to bottom to load dynamic content
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(5)
    raise TimeoutException("Table failed to load after multiple attempts.")

def scrape_table(driver, wait, table):
    """Scrape the current page's table."""
    # Verify headers
    headers = [th.text.strip() for th in table.find_elements(By.TAG_NAME, "th")]
    print(f"Found table headers: {headers}")
    
    if len(headers) < 7 or not any(word in h.lower() for h in headers for word in ['year', 'month', 'investor', 'sector', 'country', 'amount', 'type']):
        print("Warning: Unexpected table headers. Attempting to scrape anyway.")
    
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    
    for i, row in enumerate(rows[1:], 1):  # Skip header
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 7:
            try:
                year = cells[0].text.strip()
                month = cells[1].text.strip()
                investor = cells[2].text.strip()
                sector = cells[3].text.strip()
                country = cells[4].text.strip()
                amount = cells[5].text.strip()
                deal_type = cells[6].text.strip()

                data.append({
                    'Year': year,
                    'Month': month,
                    'Investor_Builder': investor,
                    'Sector': sector,
                    'Country': country,
                    'Amount': amount,
                    'Type': deal_type
                })
            except Exception as e:
                print(f"  ⚠️ Error parsing row {i}: {e}")
                continue
        elif cells:  # If fewer cells, perhaps skip or log
            print(f"  ⚠️ Row {i} has only {len(cells)} cells, skipping.")

    print(f"✓ Extracted {len(data)} rows from current page.")
    return data

def main():
    print("=" * 80)
    print("CHINA GLOBAL INVESTMENT TRACKER SCRAPER")
    print("=" * 80)
    print("Note: If no data found, the dataset may require contacting Derek Scissors at AEI for access.")

    # Setup driver
    driver = setup_driver()
    wait = WebDriverWait(driver, 120)  # Increased timeout

    all_data = []

    try:
        print(f"Loading page: {URL}")
        driver.get(URL)
        
        # Wait for page to fully load
        wait.until(lambda d: d.execute_script('return document.readyState') == "complete")
        time.sleep(5)
        
        # Handle cookies
        handle_cookies(driver, wait)
        
        # Scroll to load dynamic content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(10)

        # Scrape all pages
        page_num = 1
        while True:
            print(f"\n📄 Scraping page {page_num}...")
            table = wait_for_table(driver, wait)
            page_data = scrape_table(driver, wait, table)
            all_data.extend(page_data)

            # Check for next page button
            try:
                next_selectors = [
                    ".dataTables_paginate .next",
                    "a.next",
                    ".pagination .next"
                ]
                next_button = None
                for sel in next_selectors:
                    try:
                        next_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
                        break
                    except TimeoutException:
                        continue
                
                if next_button is None or "disabled" in next_button.get_attribute("class") or not next_button.is_enabled():
                    print("  ✓ No more pages (next disabled or not found).")
                    break
                print("  Clicking next page...")
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(5)
                page_num += 1
            except (TimeoutException, NoSuchElementException):
                print("  ✓ Reached last page (no next button).")
                break
            except Exception as e:
                print(f"  ⚠️ Pagination error: {e}")
                break

        if not all_data:
            raise ValueError("No data extracted. The dataset may not be publicly available on the page. Contact Derek Scissors at AEI for access: derek.scissors@aei.org")

        # Create DataFrame
        df = pd.DataFrame(all_data)
        print(f"\n✓ Extracted {len(df)} total rows.")
        print(f"\nPreview:\n{df.head()}")

        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)

        # Save locally
        local_csv = FILE_PATH
        df.to_csv(local_csv, index=False)
        print(f"\n✓ Data saved to {local_csv}")

        # Push to GitHub with proper authentication
        print("\nConnecting to GitHub...")
        if GITHUB_TOKEN:
            auth = Auth.Token(GITHUB_TOKEN)
            g = Github(auth=auth)
            repo = g.get_repo(REPO_NAME)

            with open(local_csv, "r", encoding="utf-8") as f:
                content = f.read()

            timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M UTC')
            commit_message = f"Update China investments data - {timestamp}"

            # Upload CSV
            try:
                # Update existing file
                file = repo.get_contents(FILE_PATH)
                repo.update_file(FILE_PATH, commit_message, content, file.sha)
                print(f"✓ Updated {FILE_PATH} in GitHub repo.")
            except Exception as e:
                if "not found" in str(e).lower() or "404" in str(e):
                    # Create new file
                    repo.create_file(FILE_PATH, commit_message, content)
                    print(f"✓ Created {FILE_PATH} in GitHub repo.")
                else:
                    raise e

            # Cleanup
            os.remove(local_csv)
        else:
            print("⚠️ No GitHub token, keeping local file")

        print("\n✅ Script completed successfully!")

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        # Save screenshot and page source for debugging
        try:
            driver.save_screenshot("error_screenshot.png")
            print("Screenshot saved as error_screenshot.png")
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Page source saved as page_source.html")
        except Exception as save_e:
            print(f"⚠️ Could not save debug files: {save_e}")
        raise e

    finally:
        driver.quit()
        print("✓ Driver closed.")

if __name__ == "__main__":
    main()
