#!/usr/bin/env python3
import pandas as pd
from datetime import datetime
from pathlib import Path
import requests
from io import StringIO

# --- Define Empires ---
EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa', 'Nigeria', 'Ghana',
    'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi', 'Botswana', 'Namibia', 'Lesotho',
    'Eswatini', 'Jamaica', 'Trinidad and Tobago', 'Barbados', 'Bahamas', 'Belize', 'Guyana',
    'Saint Lucia', 'Grenada', 'Saint Vincent and the Grenadines', 'Antigua and Barbuda',
    'Dominica', 'Saint Kitts and Nevis', 'Cyprus', 'Malta', 'Singapore', 'Malaysia', 'Brunei',
    'Bangladesh', 'Sri Lanka', 'Maldives'
}
EMPIRE_2_COUNTRIES = {'United States'}
EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan'}

CSV_URL = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/monthly_full_release_long_format.csv"
DATA_DIR = Path("data")


def download_data():
    """Download dataset from the Ember public data bucket."""
    print("Downloading dataset...")
    r = requests.get(CSV_URL)
    r.raise_for_status()
    return pd.read_csv(StringIO(r.text))


def assign_empire(country):
    """Return numeric empire ID (1, 2, 3) for a given country."""
    if country in EMPIRE_1_COUNTRIES:
        return 1
    elif country in EMPIRE_2_COUNTRIES:
        return 2
    elif country in EMPIRE_3_COUNTRIES:
        return 3
    return None


def main(local_path: str | None = None):
    # Load data (local or remote)
    df = pd.read_csv(local_path) if local_path else download_data()

    # Focus on electricity demand (TWh)
    df = df[(df["Category"] == "Electricity demand") & (df["Variable"] == "Demand")]

    # Parse date and keep latest month
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    latest_date = df["Date"].max()
    df_latest = df[df["Date"] == latest_date].copy()

    # Assign numeric empire ID
    df_latest["Empire"] = df_latest["Area"].apply(assign_empire)
    df_latest = df_latest.dropna(subset=["Empire"])

    # Select and rename columns
    df_latest = df_latest[["Empire", "Area", "Value"]]
    df_latest = df_latest.rename(columns={"Area": "Country", "Value": "Electricity_Consumption_TWh"})

    # Aggregate empire totals
    empire_totals = (
        df_latest.groupby("Empire", as_index=False)["Electricity_Consumption_TWh"]
        .sum()
        .assign(Country="Total (Empire)")
    )

    # Combine both
    combined = pd.concat([df_latest, empire_totals], ignore_index=True)
    combined = combined.sort_values(["Empire", "Country"]).reset_index(drop=True)

    # Create filename by year-month
    timestamp = latest_date.strftime("%Y-%m")
    out_file = DATA_DIR / f"empire_energy_consumption_{timestamp}.csv"

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_file, index=False)
    print(f"Saved monthly file: {out_file}")

    # Also write/update a latest symlink or copy
    latest_file = DATA_DIR / "empire_energy_consumption_latest.csv"
    combined.to_csv(latest_file, index=False)
    print(f"Updated latest snapshot: {latest_file}")


if __name__ == "__main__":
    main("monthly_full_release_long_format.csv")  # for local testing
