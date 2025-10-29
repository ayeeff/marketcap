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

    print("Setting up ChromeDriver...")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_table(driver, wait):
    """Scrape the current page's table."""
    # Wait for the table to load
    table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.dataTable")))
    rows = table.find_elements(By.TAG_NAME, "tr")

    data = []
    for row in rows[1:]:  # Skip header
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 7:  # Ensure we have enough columns
            try:
                # Extract columns: yr (year), month, investor or builder, sector, country, amount, type
                year = cells[0].text.strip()  # yr
                month = cells[1].text.strip()  # month
                investor = cells[2].text.strip()  # investor or builder
                sector = cells[3].text.strip()  # sector
                country = cells[4].text.strip()  # country
                amount = cells[5].text.strip()  # amount
                deal_type = cells[6].text.strip()  # type

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
                print(f"  ⚠️ Error parsing row: {e}")
                continue

    return data

def main():
    print("=" * 80)
    print("CHINA GLOBAL INVESTMENT TRACKER SCRAPER")
    print("=" * 80)

    # Setup driver
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)

    all_data = []

    try:
        print(f"Loading page: {URL}")
        driver.get(URL)
        time.sleep(5)  # Wait for JS to load

        # Scrape all pages
        page_num = 1
        while True:
            print(f"\n📄 Scraping page {page_num}...")
            page_data = scrape_table(driver, wait)
            all_data.extend(page_data)
            print(f"  ✓ Extracted {len(page_data)} rows from page {page_num}")

            # Check for next page button
            try:
                next_button = driver.find_element(By.CSS_SELECTOR, "a.next")
                if "disabled" in next_button.get_attribute("class") or not next_button.is_enabled():
                    print("  ✓ No more pages")
                    break
                next_button.click()
                time.sleep(3)  # Wait for page load
                page_num += 1
            except Exception:
                print("  ✓ Reached last page")
                break

        if not all_data:
            raise ValueError("No data extracted from table")

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
        raise e

    finally:
        driver.quit()
        print("✓ Driver closed.")

if __name__ == "__main__":
    main()
