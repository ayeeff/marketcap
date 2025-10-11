import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service  # Required for Selenium 4.6+
from github import Github
import time

# Configuration
URL = "https://www.marketcapwatch.com/all-countries/"
REPO_NAME = "ayeeff/marketcap"
FILE_PATH = "data/countries_marketcap.csv"
# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Secure: Set via export or Codespaces secrets

# For testing only (insecure - remove after testing):
GITHUB_TOKEN = "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"

# Validate token
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable not set. Run: export GITHUB_TOKEN=your_token_here")
print("GitHub token loaded successfully.")  # Debug print - remove later

# Set up Selenium with system Chromium (Codespaces-optimized)
chrome_options = Options()
chrome_options.add_argument('--headless')  # Headless mode
chrome_options.add_argument('--no-sandbox')  # Bypass OS security model
chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resources
chrome_options.add_argument('--disable-gpu')  # Disable GPU (container env)
chrome_options.add_argument('--remote-debugging-port=9222')  # Fix potential port errors
chrome_options.add_argument('--window-size=1920,1080')  # Set window size
chrome_options.binary_location = '/usr/bin/chromium-browser'  # Point to installed binary

# Use system chromedriver with Service (fixes the executable_path error)
service = Service(executable_path='/usr/bin/chromedriver')
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Load the page
    print("Loading page...")
    driver.get(URL)
    
    # Wait for the table to load
    wait = WebDriverWait(driver, 20)
    table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
    print("Table found!")
    
    # Extract table data
    rows = table.find_elements(By.TAG_NAME, "tr")
    data = []
    for row in rows:
        cells = [cell.text.strip() for cell in row.find_elements(By.TAG_NAME, "th, td")]
        if cells:  # Skip empty rows
            data.append(cells)
    
    if not data:
        raise ValueError("No table data found. Check the table selector.")
    
    # Create DataFrame
    columns = data[0]
    df = pd.DataFrame(data[1:], columns=columns)
    print(f"Extracted {len(df)} rows of data.")
    
    # Save to local CSV
    local_csv = "countries_marketcap.csv"
    df.to_csv(local_csv, index=False)
    print(f"Data saved to {local_csv}")
    
    # Upload to GitHub
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    # Read the CSV content
    with open(local_csv, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check if file exists and update or create
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
    
    # Clean up local file
    os.remove(local_csv)
    print("Script completed successfully!")

finally:
    driver.quit()
    print("Driver closed.")
