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
URL = "https://www.marketcapwatch.com/all-countries/"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/countries_marketcap.csv"

# Load token from environment variable (NEVER hardcode tokens!)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError(
        "GITHUB_TOKEN environment variable not set.\n"
        "Run: export GITHUB_TOKEN=your_token_here"
    )

print("✓ GitHub token loaded successfully.")

# Selenium setup
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
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Loading page: {URL}")
    driver.get(URL)
    
    # Wait for JavaScript to load
    time.sleep(5)
    
    # Find table
    wait = WebDriverWait(driver, 20)
    tables = driver.find_elements(By.TAG_NAME, "table")
    
    if not tables:
        raise ValueError("No tables found on page")
    
    table = tables[0]
    print("✓ Table found!")
    
    # Extract table data
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    
    for row in rows:
        # Get both th and td elements
        cells_th = row.find_elements(By.TAG_NAME, "th")
        cells_td = row.find_elements(By.TAG_NAME, "td")
        all_cells = cells_th + cells_td
        
        # Extract text from cells
        cells = [cell.text.strip() for cell in all_cells]
        
        # Only add rows that have content
        if cells and any(cell for cell in cells):
            data.append(cells)
    
    if not data:
        raise ValueError("No data extracted from table")
    
    # Create DataFrame
    columns = data[0]
    df = pd.DataFrame(data[1:], columns=columns)
    print(f"✓ Extracted {len(df)} rows of data.")
    print(f"\nPreview:\n{df.head()}")
    
    # Save locally
    local_csv = "countries_marketcap.csv"
    df.to_csv(local_csv, index=False)
    print(f"\n✓ Data saved to {local_csv}")
    
    # Push to GitHub with proper authentication
    print("\nConnecting to GitHub...")
    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
    repo = g.get_repo(REPO_NAME)
    
    with open(local_csv, "r", encoding="utf-8") as f:
        content = f.read()
    
    timestamp = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M UTC')
    commit_message = f"Update countries market cap data - {timestamp}"
    
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
    print("\n✅ Script completed successfully!")

except Exception as e:
    print(f"\n❌ Error occurred: {e}")
    import traceback
    traceback.print_exc()
    raise e

finally:
    driver.quit()
    print("✓ Driver closed.")
