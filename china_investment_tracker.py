import os
import pandas as pd
import requests
from github import Github, Auth
from io import BytesIO

# Configuration
XLS_URL = "https://www.aei.org/wp-content/uploads/2020/01/China-Global-Investment-Tracker-2019-Fall-FINAL.xlsx"
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

def download_and_parse_xls():
    """Download the XLS file and parse it into a DataFrame."""
    print(f"Downloading XLS from: {XLS_URL}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    response = requests.get(XLS_URL, headers=headers)
    response.raise_for_status()

    # Read Excel from bytes
    xls_data = BytesIO(response.content)
    df = pd.read_excel(xls_data, sheet_name="Dataset 1", skiprows=3)  # Skip header rows if needed

    print(f"✓ Loaded DataFrame with {len(df)} rows and columns: {list(df.columns)}")

    # Map to required columns (adjust based on actual column names)
    # Assuming columns: ['Unnamed: 0', 'Year', 'Month', 'Parent Company', 'Amount', 'Phase', 'Industry', 'Sub-Industry', 'Host Country', 'Region', 'Deal Type']
    column_mapping = {
        'Year': 'Year',
        'Month': 'Month',
        'Parent Company': 'Investor_Builder',
        'Industry': 'Sector',
        'Host Country': 'Country',
        'Amount': 'Amount',
        'Deal Type': 'Type'
    }

    # Select and rename columns
    available_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
    df_selected = df[list(available_cols.keys())].rename(columns={k: column_mapping[k] for k in available_cols})

    # Clean data if needed (e.g., extract year from date if full date)
    if 'Year' in df_selected.columns and df_selected['Year'].dtype == 'object':
        df_selected['Year'] = df_selected['Year'].astype(str).str[:4]

    print(f"✓ Selected columns: {list(df_selected.columns)}")
    print(f"Sample data:\n{df_selected.head()}")

    return df_selected

def main():
    print("=" * 80)
    print("CHINA GLOBAL INVESTMENT TRACKER DOWNLOADER & PARSER")
    print("=" * 80)
    print("Note: Public table not available; using latest available XLS (2019 data). For current data, contact Derek Scissors at AEI.")

    df = download_and_parse_xls()

    if df.empty:
        raise ValueError("No data extracted from XLS")

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
        commit_message = f"Update China investments data (2019 XLS) - {timestamp}"

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

if __name__ == "__main__":
    main()
