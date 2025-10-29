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
import undetected_chromedriver as uc

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
    """Setup undetected Chrome driver to bypass Cloudflare."""
    print("Setting up undetected ChromeDriver...")
    
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    
    # Use undetected_chromedriver
    driver = uc.Chrome(options=options, version_main=None)
    
    return driver

def wait_for_cloudflare(driver, timeout=30):
    """Wait for Cloudflare check to complete."""
    print("Checking for Cloudflare protection...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        title = driver.title.lower()
        
        if "just a moment" in title or "checking your browser" in title:
            print(f"  ⏳ Cloudflare detected, waiting... ({int(time.time() - start_time)}s)")
            time.sleep(2)
        else:
            print(f"  ✓ Cloudflare passed! Title: {driver.title}")
            return True
    
    raise TimeoutException("Cloudflare check did not complete in time")

def wait_for_datatable(driver, timeout=30):
    """Wait for DataTable to initialize and load data."""
    print("Waiting for DataTable to initialize...")
    
    # Wait for jQuery and DataTable to be loaded
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return typeof jQuery !== 'undefined'")
        )
        print("  ✓ jQuery loaded")
    except TimeoutException:
        print("  ⚠️ jQuery not detected, trying anyway...")
    
    # Wait for DataTable library
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return jQuery.fn.DataTable !== undefined")
        )
        print("  ✓ DataTable library loaded")
    except TimeoutException:
        print("  ⚠️ DataTable not detected, trying to find table anyway...")
    
    # Wait for table to exist and have data
    WebDriverWait(driver, timeout).until(
        lambda d: len(d.find_elements(By.CSS_SELECTOR, "table tbody tr")) > 0
    )
    print("  ✓ Table has data")
    
    # Wait for any processing overlay to disappear
    time.sleep(2)
    print("  ✓ Ready to scrape")

def get_total_entries(driver):
    """Get total number of entries from DataTable info."""
    try:
        info_text = driver.find_element(By.CSS_SELECTOR, ".dataTables_info").text
        import re
        match = re.search(r'of\s+([\d,]+)\s+entries', info_text)
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
        # Try multiple selectors
        next_selectors = [
            "#dataTable_next",
            ".dataTables_paginate .next",
            "a.paginate_button.next",
            ".pagination .next"
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
        if "disabled" in classes:
            return False
        
        # Click using JavaScript
        driver.execute_script("arguments[0].click();", next_button)
        
        # Wait for page to update
        time.sleep(3)
        
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
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(3)
        
        # Wait for DataTable
        wait_for_datatable(driver)
        
        # Get total entries
        total_entries = get_total_entries(driver)
        
        # Scrape all pages
        page_num = 1
        max_pages = 30  # Safety limit
        consecutive_empty = 0
        
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
        print(f"\n✓ Extracted {len(df)} total rows.")
        print(f"\nFirst 5 rows:\n{df.head()}")
        print(f"\nLast 5 rows:\n{df.tail()}")

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

            if not os.getenv("CI"):  # Keep file locally if not in CI
                print("✓ Keeping local file (not in CI)")
            else:
                os.remove(local_csv)
        else:
            print("⚠️ No GitHub token, keeping local file")

        print("\n✅ Script completed successfully!")

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
