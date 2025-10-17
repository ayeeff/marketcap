import os
import pandas as pd
from datetime import datetime

DATA_URL = "https://storage.googleapis.com/emb-prod-bkt-publicdata/public-downloads/monthly_full_release_long_format.csv"

EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa', 'Nigeria', 'Ghana',
    'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi', 'Botswana', 'Namibia', 'Lesotho', 'Eswatini',
    'Jamaica', 'Trinidad and Tobago', 'Barbados', 'Bahamas', 'Belize', 'Guyana', 'Saint Lucia',
    'Grenada', 'Saint Vincent and the Grenadines', 'Antigua and Barbuda', 'Dominica',
    'Saint Kitts and Nevis', 'Cyprus', 'Malta', 'Singapore', 'Malaysia', 'Brunei', 'Bangladesh',
    'Sri Lanka', 'Maldives'
}
EMPIRE_2_COUNTRIES = {'United States'}
EMPIRE_3_COUNTRIES = {'China', 'Hong Kong', 'Taiwan'}

def download_data() -> pd.DataFrame:
    print(f"🌐 Downloading dataset from {DATA_URL} ...")
    df = pd.read_csv(DATA_URL, low_memory=False)
    return df

def assign_empire(area: str) -> int | None:
    if area in EMPIRE_1_COUNTRIES:
        return 1
    elif area in EMPIRE_2_COUNTRIES:
        return 2
    elif area in EMPIRE_3_COUNTRIES:
        return 3
    return None

def main():
    df = download_data()

    # Clean up column names for consistency
    df.columns = df.columns.str.strip()

    # Filter for electricity consumption
    df_elec = df[df["Indicator"].str.contains("Electricity", case=False, na=False)]

    # Assign empire codes
    df_elec["Empire"] = df_elec["Area"].apply(assign_empire)
    df_elec = df_elec.dropna(subset=["Empire"])

    # Aggregate total electricity consumption per country
    result = (
        df_elec.groupby(["Empire", "Area"], as_index=False)["Value"]
        .sum()
        .sort_values(["Empire", "Value"], ascending=[True, False])
    )

    # Output directory
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m")
    output_path = f"data/empire_energy_consumption_{timestamp}.csv"
    result.to_csv(output_path, index=False)

    print(f"✅ Saved empire electricity summary → {output_path}")
    print(result.head(10))

if __name__ == "__main__":
    main()
