# Market Cap Scraper

## Overview
This is a Python web scraping project that extracts country-level stock market capitalization data from MarketCapWatch.com. The script uses Selenium with headless Chromium to scrape the data, saves it to a CSV file, and optionally uploads it to a GitHub repository.

## Project Structure
- `main.py` - Main scraping script
- `data/` - Directory for CSV output
- `countries_marketcap.csv` - Generated CSV file with scraped data
- `.gitignore` - Git ignore file for Python projects

## Features
- Scrapes market capitalization data for ~90 countries
- Uses Selenium WebDriver with headless Chromium browser
- Handles JavaScript-rendered content
- Saves data to CSV format
- Optional GitHub integration for automatic repository updates

## Technical Setup
- **Language**: Python 3.11
- **Dependencies**: 
  - pandas - Data manipulation
  - selenium - Web scraping
  - webdriver-manager - ChromeDriver management
  - PyGithub - GitHub API integration

- **System Dependencies**:
  - chromium - Headless browser
  - chromedriver - Selenium WebDriver for Chromium

## Configuration
The script requires the following configuration (set in `main.py`):
- `URL`: Target website (currently MarketCapWatch.com)
- `REPO_NAME`: GitHub repository name (format: "username/repo")
- `FILE_PATH`: Path in repo where CSV should be saved
- `GITHUB_TOKEN` (optional): GitHub Personal Access Token (set as environment variable)

## Running the Script
The script runs automatically via the "Scraper" workflow. It can also be run manually:
```bash
python main.py
```

## GitHub Integration (Optional)
To enable automatic GitHub uploads:
1. Create a GitHub Personal Access Token with repo permissions
2. Set it as the `GITHUB_TOKEN` environment variable
3. Configure `REPO_NAME` and `FILE_PATH` in main.py

Without the token, the script will save the CSV locally only.

## Output
The script generates `countries_marketcap.csv` with columns:
- Rank
- Country or region
- Total MarketCap
- Total Companies

## Recent Changes
- **2025-10-11**: Initial setup in Replit environment
  - Installed Python 3.11 with required packages
  - Configured Selenium with Chromium/ChromeDriver
  - Fixed text extraction to use `textContent` attribute for JavaScript-rendered content
  - Made GitHub upload optional
  - Added comprehensive error handling and debug output
