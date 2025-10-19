import os
import pandas as pd
from datetime import datetime

# ------------------------------------------------------------------
# 1.  DATA  –  NEW ANNUAL FILE
# ------------------------------------------------------------------
DATA_URL = ("https://storage.googleapis.com/emb-prod-bkt-publicdata/"
            "public-downloads/yearly_full_release_long_format.csv")

# ------------------------------------------------------------------
# 2.  EMPIRE LOOKUPS  (unchanged)
# ------------------------------------------------------------------
EMPIRE_1_COUNTRIES = {
    'United Kingdom', 'Canada', 'Australia', 'New Zealand', 'South Africa',
    'Nigeria', 'Ghana', 'Kenya', 'Uganda', 'Tanzania', 'Zambia', 'Malawi',
    'Botswana', 'Namibia', 'Lesotho', 'Eswatini', 'Jamaica',
    'Trinidad and Tobago', 'Barbados', 'Bahamas', 'Belize', 'Guyana',
    'Saint Lucia', 'Grenada', 'Saint Vincent and the Grenadines',
    'Antigua and Barbuda', 'Dominica', 'Saint Kitts and Nevis',
    'Cyprus', 'Malta', 'Singapore', 'Malaysia', 'Brunei', 'Bangladesh',
    'Sri Lanka', 'Maldives'
}
EMPIRE_2_COUNTRIES = {'United States of America'}
EMPIRE_3_COUNTRIES = {'China', 'Hong Kong (China)', 'Taiwan'}

def assign_empire(area: str) -> int | None:
    if area in EMPIRE_1_COUNTRIES:
        return 1
    if area in EMPIRE_2_COUNTRIES:
        return 2
    if area in EMPIRE_3_COUNTRIES:
        return 3
    return None

# ------------------------------------------------------------------
# 3.  DOWNLOAD
# ------------------------------------------------------------------
def download_data() -> pd.DataFrame:
    print(f"🌐  Downloading … {DATA_URL}")
    df = pd.read_csv(DATA_URL, low_memory=False)
    print(f"✅  Loaded {len(df):,} rows × {len(df.columns)} columns")
    return df

# ------------------------------------------------------------------
# 4.  MAIN PIPELINE
# ------------------------------------------------------------------
def main():
    df = download_data()

    # ---- 4a.  keep only electricity-related rows -----------------
    elec_mask = df.select_dtypes(include='object') \
                  .apply(lambda s: s.str.contains('Electric', case=False, na=False)) \
                  .any(axis=1)
    df_elec = df[elec_mask].copy()

    # ---- 4b.  empire column (int, no decimals) -------------------
    df_elec['Empire'] = df_elec['Area'].apply(assign_empire)
    df_elec = df_elec.dropna(subset=['Empire'])
    df_elec['Empire'] = df_elec['Empire'].astype('int64')

    # ---- 4c.  country totals -------------------------------------
    by_country = (
        df_elec.groupby(['Empire', 'Area'], as_index=False)['Value']
        .sum()
        .sort_values(['Empire', 'Value'], ascending=[True, False])
    )

    # ---- 4d.  empire sub-totals ----------------------------------
    empire_totals = (
        by_country.groupby('Empire', as_index=False)['Value']
        .sum()
        .assign(Area='Total')
    )

    # ---- 4e.  combine countries + their total row ----------------
    final = (
        pd.concat([by_country, empire_totals], ignore_index=True)
          .sort_values(['Empire', 'Value'], ascending=[True, False])
          .reset_index(drop=True)
    )

    # ---- 4f.  save -----------------------------------------------
    os.makedirs('data', exist_ok=True)
    out_file = 'data/empire_energy_consumption.csv'
    final.to_csv(out_file, index=False)
    print(f'\n✅  Saved → {out_file}\n')
    print(final)

# ------------------------------------------------------------------
if __name__ == '__main__':
    main()
