# Importeren van benodigde libraries
import pandas as pd
from IPython.display import display
import warnings

# Waarschuwingen negeren
warnings.filterwarnings('ignore')

# Functie om data in te laden
def load_data():
    # Lees de Excel-bestanden in DataFrames
    df_omloopplanning = pd.read_excel('omloopplanning.xlsx', engine='openpyxl')
    df_dienstregeling = pd.read_excel('Connexxion data - 2024-2025.xlsx', engine='openpyxl')
    return df_omloopplanning, df_dienstregeling

def check_omloopplanning(omloop_df, dienst_df):
    # Voeg een nieuwe kolom toe om de correctheid te markeren
    omloop_df['correct'] = False

    # Filter alleen op dienstritten in omloopplanning
    dienst_ritten_omloop = omloop_df[omloop_df['activiteit'] == 'dienst rit']
    
    for idx, row in dienst_ritten_omloop.iterrows():
        # Filter voor de overeenkomstige rijen in de dienstregeling
        dienst_rows = dienst_df[
            (dienst_df['startlocatie'] == row['startlocatie']) &
            (dienst_df['eindlocatie'] == row['eindlocatie']) &
            (dienst_df['buslijn'] == row['buslijn'])
        ]
        
        for _, dienst_row in dienst_rows.iterrows():
            # Maak een vertrektijd datetime object
            if pd.isna(row['starttijd']):
                print(f"Skipping row {idx} because of NaT (Not a Time)")
                continue
            
            vertrektijd = pd.to_datetime(f"{row['starttijd'].date()} {dienst_row['vertrektijd'].strip()}")
            
            # Controleer of de starttijd overeenkomt met de dienstregeling
            if vertrektijd == row['starttijd']:
                omloop_df.at[idx, 'correct'] = True
                break

    # Controleer of alle ritten in de dienstregeling aanwezig zijn in de omloopplanning
    dienst_df['found_in_omloop'] = False

    for idx, row in dienst_df.iterrows():
        try:
            omloop_rows = omloop_df[
                (omloop_df['startlocatie'] == row['startlocatie']) &
                (omloop_df['eindlocatie'] == row['eindlocatie']) &
                (omloop_df['buslijn'] == row['buslijn']) &
                (omloop_df['starttijd'].dt.time == pd.to_datetime(f"{row['vertrektijd']}").time()) &
                (omloop_df['activiteit'] == 'dienst rit')
            ]
        except ValueError as e:
            print(f"Error in row {idx}: {str(e)}")
            continue

        if not omloop_rows.empty:
            dienst_df.at[idx, 'found_in_omloop'] = True

    return omloop_df, dienst_df
