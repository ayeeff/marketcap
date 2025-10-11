# Line 1-10: Imports
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service  # CRITICAL: For Selenium 4.6+ driver setup
from github import Github
import time

# Line 12-18: Configuration
URL = "https://www.marketcapwatch.com/all-countries/"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/countries_marketcap.csv"
# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Secure: Set via export or Codespaces secrets

# Line 20-22: Token fallback for testing (insecure - comment out after)
GITHUB_TOKEN = "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"

# Line 24-26: Validate token
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable not set. Run: export GITHUB_TOKEN=your_token_here")
print("GitHub token loaded successfully.")  # Debug: Remove after success

# Line 28-36: Selenium setup
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--remote-debugging-port=9222')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.binary_location = '/usr/bin/chromium-browser'

# Line 38-39: CRITICAL FIX - Use Service for driver path
service = Service(executable_path='/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=chrome_options)  # NO 'executable_path' here!

# Line 41-80: Rest of script (unchanged)
try:
    print("Loading page...")
    driver.get(URL)
    
    wait = WebDriverWait(driver, 20)
    table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    print("Table found!")
    
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    for row in rows:
        cells = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, "th, td")]
        if cells:
            data.append(cells)
    
    if not data:
        raise ValueError("No table data found. Check the table selector.")
    
    columns = data[0]
    df = pd.DataFrame(data[1:], columns=columns)
    print(f"Extracted {len(df)} rows of data.")
    
    local_csv = "countries_marketcap.csv"
    df.to_csv(local_csv, index=False)
    print(f"Data saved to {local_csv}")
    
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    with open(local_csv, "r", encoding="utf-8") as f:
        content = f.read()
    
    try:
        file = repo.get_contents(FILE_PATH)
        repo.update_file(FILE_PATH, "Update countries market cap data", content, file.sha)
        print(f"Updated {FILE_PATH} in GitHub repo.")
    except Exception as e:
        if "not found" in str(e).lower():
            repo.create_file(FILE_PATH, "Add countries market cap data", content)
            print(f"Created {FILE_PATH} in GitHub repo.")
        else:
            print(f"GitHub error: {e}")
            raise e
    
    os.remove(local_csv)
    print("Script completed successfully!")

finally:
    driver.quit()
    print("Driver closed.")
