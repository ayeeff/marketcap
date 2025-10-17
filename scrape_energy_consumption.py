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
OUTPUT_PATH = Path("data/empire_energy_consumption.csv")


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

    # Parse date and keep only the latest month
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    latest_date = df["Date"].max()
    df_latest = df[df["Date"] == latest_date].copy()

    # Add numeric Empire ID
    df_latest["Empire"] = df_latest["Area"].apply(assign_empire)
    df_latest = df_latest.dropna(subset=["Empire"])

    # Select and rename columns
    df_latest = df_latest[["Empire", "Area", "Value"]]
    df_latest = df_latest.rename(columns={"Area": "Country", "Value": "Electricity_Consumption_TWh"})

    # Aggregate totals per empire
    empire_totals = (
        df_latest.groupby("Empire", as_index=False)["Electricity_Consumption_TWh"]
        .sum()
        .assign(Country="Total (Empire)")
    )

    # Combine country-level + empire totals
    combined = pd.concat([df_latest, empire_totals], ignore_index=True)
    combined = combined.sort_values(["Empire", "Country"]).reset_index(drop=True)

    # Save to CSV
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved combined CSV to {OUTPUT_PATH}")
    print(combined.head(10))


if __name__ == "__main__":
    # Local test mode
    main("monthly_full_release_long_format.csv")
