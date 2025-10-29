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
from selenium_stealth import stealth
from github import Github, Auth
import time

# Configuration
URL = "https://www.aei.org/china-global-investment-tracker/"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/china_investments.csv"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN and not os.getenv("CI"):
    raise ValueError("GITHUB_TOKEN environment variable not set.\nRun: export GITHUB_TOKEN=your_token_here")

if GITHUB_TOKEN:
    print("✓ GitHub token loaded successfully.")

def setup_driver():
    """Setup Chrome driver with stealth mode to bypass Cloudflare."""
    print("Setting up ChromeDriver with anti-detection...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Apply stealth settings
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Linux",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
    )
    
    return driver

def wait_for_cloudflare(driver, timeout=40):
    """Wait for Cloudflare check to complete."""
    print("Checking for Cloudflare protection...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        title = driver.title.lower()
        
        if "just a moment" in title or "checking your browser" in title:
            elapsed = int(time.time() - start_time)
            print(f"  ⏳ Cloudflare detected, waiting... ({elapsed}s)")
            time.sleep(3)
        else:
            print(f"  ✓ Cloudflare passed! Title: {driver.title}")
            return True
    
    raise TimeoutException("Cloudflare check did not complete in time")

def wait_for_datatable(driver, timeout=30):
    """Wait for DataTable to initialize and load data."""
    print("Waiting for DataTable to initialize...")
    
    # First, just wait for any table with data
    WebDriverWait(driver, timeout).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "table tbody tr")) > 0
    )
    print("  ✓ Table with data found")
    
    # Check if jQuery/DataTable exists
    try:
        has_jquery = driver.execute_script("return typeof jQuery !== 'undefined'")
        if has_jquery:
            print("  ✓ jQuery detected")
            has_datatable = driver.execute_script("return typeof jQuery.fn.DataTable !== 'undefined'")
            if has_datatable:
                print("  ✓ DataTable detected")
    except:
        print("  ⚠️ jQuery/DataTable not detected, but table exists")
    
    # Extra wait for any loading
    time.sleep(3)
    print("  ✓ Ready to scrape")

def get_total_entries(driver):
    """Get total number of entries from DataTable info."""
    try:
        # Try multiple selectors
        selectors = [".dataTables_info", ".table-info", "[class*='info']"]
        info_text = None
        
        for selector in selectors:
            try:
                info_text = driver.find_element(By.CSS_SELECTOR, selector).text
                break
            except:
                continue
        
        if info_text:
            import re
            match = re.search(r'of\s+([\d,]+)\s+entries', info_text, re.IGNORECASE)
            if match:
                total = int(match.group(1).replace(',', ''))
                print(f"✓ Total entries found: {total}")
                return total
    except Exception as e:
        print(f"⚠️ Could not get total entries: {e}")
    return None

def scrape_current_page(driver):
    """Scrape data from the current page."""
    # Try different table selectors
    table = None
    for selector in ["table.dataTable", "table.table", "table"]:
        try:
            table = driver.find_element(By.CSS_SELECTOR, selector)
            break
        except:
            continue
    
    if not table:
        raise Exception("Could not find table on page")
    
    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
    
    data = []
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 7:
            try:
                data.append({
                    'Year': cells[0].text.strip(),
                    'Month': cells[1].text.strip(),
                    'Investor_Builder': cells[2].text.strip(),
                    'Sector': cells[3].text.strip(),
                    'Country': cells[4].text.strip(),
                    'Amount': cells[5].text.strip(),
                    'Type': cells[6].text.strip()
                })
            except Exception as e:
                print(f"  ⚠️ Error parsing row: {e}")
                continue
    
    return data

def click_next_page(driver):
    """Click the next page button. Returns True if successful, False if no more pages."""
    try:
        # Try multiple selectors for next button
        next_selectors = [
            "#dataTable_next",
            ".dataTables_paginate .next",
            "a.paginate_button.next",
            ".pagination .next",
            "[aria-label='Next']",
            "a:contains('Next')"
        ]
        
        next_button = None
        for selector in next_selectors:
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                continue
        
        if not next_button:
            return False
        
        # Check if disabled
        classes = next_button.get_attribute("class") or ""
        aria_disabled = next_button.get_attribute("aria-disabled") or ""
        
        if "disabled" in classes or aria_disabled == "true":
            return False
        
        # Scroll to button
        driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
        time.sleep(1)
        
        # Click using JavaScript
        driver.execute_script("arguments[0].click();", next_button)
        
        # Wait for page to update
        time.sleep(4)
        
        return True
    except Exception as e:
        print(f"  ⚠️ Error clicking next: {e}")
        return False

def main():
    print("=" * 80)
    print("CHINA GLOBAL INVESTMENT TRACKER SCRAPER")
    print("=" * 80)

    driver = setup_driver()
    all_data = []

    try:
        print(f"\nLoading page: {URL}")
        driver.get(URL)
        
        # Wait for Cloudflare
        wait_for_cloudflare(driver)
        
        # Additional wait for page to fully load
        time.sleep(5)
        
        print(f"✓ Current page title: {driver.title}")
        
        # Scroll to trigger any lazy loading
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(2)
        
        # Wait for DataTable
        wait_for_datatable(driver)
        
        # Get total entries
        total_entries = get_total_entries(driver)
        
        # Scrape all pages
        page_num = 1
        max_pages = 30  # Safety limit
        consecutive_empty = 0
        last_data_count = 0
        
        while page_num <= max_pages:
            print(f"\n📄 Scraping page {page_num}...")
            
            try:
                page_data = scrape_current_page(driver)
                
                if not page_data:
                    consecutive_empty += 1
                    print(f"  ⚠️ No data on this page (empty count: {consecutive_empty})")
                    if consecutive_empty >= 3:
                        print("  ✓ Multiple empty pages, stopping")
                        break
                else:
                    consecutive_empty = 0
                    all_data.extend(page_data)
                    print(f"  ✓ Extracted {len(page_data)} rows (Total: {len(all_data)})")
                    
                    # Check if we're getting duplicate data (stuck on same page)
                    if len(all_data) == last_data_count:
                        print("  ⚠️ No new data added, might be stuck")
                        break
                    last_data_count = len(all_data)
                
                # Progress indicator
                if total_entries:
                    progress = (len(all_data) / total_entries) * 100
                    print(f"  Progress: {progress:.1f}% ({len(all_data)}/{total_entries})")
                
                # Check if we have all data
                if total_entries and len(all_data) >= total_entries:
                    print(f"  ✓ Reached all {total_entries} entries!")
                    break
                
            except Exception as e:
                print(f"  ⚠️ Error scraping page {page_num}: {e}")
            
            # Try to go to next page
            if not click_next_page(driver):
                print("  ✓ No more pages available")
                break
            
            page_num += 1

        if not all_data:
            # Save debug info
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot("error_screenshot.png")
            raise ValueError("No data extracted. Check page_source.html and error_screenshot.png for details.")

        # Create DataFrame
        df = pd.DataFrame(all_data)
        print(f"\n{'='*80}")
        print(f"✓ SUCCESSFULLY EXTRACTED {len(df)} TOTAL ROWS")
        print(f"{'='*80}")
        print(f"\nFirst 5 rows:\n{df.head()}")
        print(f"\nLast 5 rows:\n{df.tail()}")
        
        # Show unique years to verify data range
        if 'Year' in df.columns:
            years = df['Year'].unique()
            print(f"\nYears in dataset: {sorted(years)}")

        # Save locally
        os.makedirs('data', exist_ok=True)
        local_csv = FILE_PATH
        df.to_csv(local_csv, index=False)
        print(f"\n✓ Data saved to {local_csv}")

        # Push to GitHub
        if GITHUB_TOKEN:
            print("\nPushing to GitHub...")
            auth = Auth.Token(GITHUB_TOKEN)
            g = Github(auth=auth)
            repo = g.get_repo(REPO_NAME)

            with open(local_csv, "r", encoding="utf-8") as f:
                content = f.read()

            timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M UTC')
            commit_message = f"Update China investments data - {timestamp} - {len(df)} entries"

            try:
                file = repo.get_contents(FILE_PATH)
                repo.update_file(FILE_PATH, commit_message, content, file.sha)
                print(f"✓ Updated {FILE_PATH} in GitHub repo.")
            except Exception as e:
                if "not found" in str(e).lower() or "404" in str(e):
                    repo.create_file(FILE_PATH, commit_message, content)
                    print(f"✓ Created {FILE_PATH} in GitHub repo.")
                else:
                    raise e

            if not os.getenv("CI"):
                print("✓ Keeping local file (not in CI)")
            else:
                os.remove(local_csv)
        else:
            print("⚠️ No GitHub token, keeping local file")

        print("\n✅ SCRIPT COMPLETED SUCCESSFULLY!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            driver.save_screenshot("error_screenshot.png")
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Debug files saved: error_screenshot.png, page_source.html")
        except:
            pass
        
        raise e

    finally:
        driver.quit()
        print("✓ Driver closed.")

if __name__ == "__main__":
    main()
