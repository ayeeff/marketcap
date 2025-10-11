import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from github import Github
import time

# Configuration
URL = "https://www.marketcapwatch.com/all-countries/"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/countries_marketcap.csv"

# SECURE: Load token from environment variable
GITHUB_TOKEN = "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" 

# Validate token
if not GITHUB_TOKEN:
    raise ValueError(
        "GITHUB_TOKEN environment variable not set.\n"
        "Run: export GITHUB_TOKEN=your_token_here\n"
        "Or in Codespaces: Add to repository secrets"
    )

print("✓ GitHub token loaded successfully.")

# Selenium setup with Chrome - using webdriver-manager for auto driver handling
chrome_options = Options()
chrome_options.add_argument('--headless=new')  # Updated headless mode
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-software-rasterizer')
chrome_options.add_argument('--remote-debugging-port=9222')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Try to use system Chrome/Chromium, fallback to auto-detection
try:
    chrome_options.binary_location = '/usr/bin/chromium-browser'
except:
    pass

# Use webdriver-manager to automatically download and manage ChromeDriver
print("Setting up ChromeDriver...")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Loading page: {URL}")
    driver.get(URL)
    
    # Wait for table to load
    wait = WebDriverWait(driver, 20)
    table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    print("✓ Table found!")
    
    # Extract table data
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    for row in rows:
        cells = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, "th, td")]
        if cells:
            data.append(cells)
    
    if not data:
        raise ValueError("No table data found. Check the table selector.")
    
    # Create DataFrame
    columns = data[0]
    df = pd.DataFrame(data[1:], columns=columns)
    print(f"✓ Extracted {len(df)} rows of data.")
    print(f"\nPreview:\n{df.head()}")
    
    # Save locally (temporary)
    local_csv = "countries_marketcap.csv"
    df.to_csv(local_csv, index=False)
    print(f"\n✓ Data saved to {local_csv}")
    
    # Push to GitHub
    print("\nConnecting to GitHub...")
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    with open(local_csv, "r", encoding="utf-8") as f:
        content = f.read()
    
    try:
        # Try to update existing file
        file = repo.get_contents(FILE_PATH)
        repo.update_file(
            FILE_PATH, 
            f"Update countries market cap data - {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}", 
            content, 
            file.sha
        )
        print(f"✓ Updated {FILE_PATH} in GitHub repo.")
    except Exception as e:
        if "not found" in str(e).lower():
            # Create new file if it doesn't exist
            repo.create_file(
                FILE_PATH, 
                "Add countries market cap data", 
                content
            )
            print(f"✓ Created {FILE_PATH} in GitHub repo.")
        else:
            print(f"GitHub error: {e}")
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
