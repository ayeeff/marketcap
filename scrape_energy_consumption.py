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
    print(f"✅ Loaded {len(df):,} rows, {len(df.columns)} columns.")
    print("📊 Columns:", list(df.columns))
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
    df.columns = df.columns.str.strip()

    # Try to find the column describing what the data measures
    possible_cols = [c for c in df.columns if df[c].astype(str).str.contains("Electric", case=False, na=False).any()]
    if not possible_cols:
        print("⚠️ No electricity-related column found automatically. Defaulting to all rows.")
        df_elec = df.copy()
    else:
        chosen_col = possible_cols[0]
        print(f"⚡ Using column '{chosen_col}' to filter electricity data.")
        df_elec = df[df[chosen_col].astype(str).str.contains("Electric", case=False, na=False)]

    # Assign empire based on Area
    if "Area" not in df_elec.columns:
        raise KeyError("❌ 'Area' column missing — cannot assign countries to empires.")
    df_elec["Empire"] = df_elec["Area"].apply(assign_empire)
    df_elec = df_elec.dropna(subset=["Empire"])

    # Aggregate
    if "Value" not in df_elec.columns:
        raise KeyError("❌ 'Value' column missing — cannot sum consumption data.")
    result = (
        df_elec.groupby(["Empire", "Area"], as_index=False)["Value"]
        .sum()
        .sort_values(["Empire", "Value"], ascending=[True, False])
    )

    # Save output
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m")
    output_path = f"data/empire_energy_consumption_{timestamp}.csv"
    result.to_csv(output_path, index=False)

    print(f"✅ Saved empire electricity summary → {output_path}")
    print(result.head(15))

if __name__ == "__main__":
    main()
