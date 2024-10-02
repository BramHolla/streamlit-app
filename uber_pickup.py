# Zorg ervoor dat de juiste bibliotheken zijn geïmporteerd
import streamlit as st
import pandas as pd
import warnings
import openpyxl

# Waarschuwingen negeren
warnings.filterwarnings('ignore')

def load_data(uploaded_file_1, uploaded_file_2):
    # Lees de geüploade bestanden in DataFrames
    df_omloopplanning = pd.read_excel(uploaded_file_1, engine='openpyxl')
    df_dienstregeling = pd.read_excel(uploaded_file_2, engine='openpyxl')

    # Zorg ervoor dat 'starttijd' kolom datetime is
    df_omloopplanning['starttijd'] = pd.to_datetime(df_omloopplanning['starttijd'], errors='coerce')

    return df_omloopplanning, df_dienstregeling

def check_omloopplanning(omloop_df, dienst_df):
    # Voeg een nieuwe kolom toe om de correctheid te markeren
    omloop_df['correct'] = False

    # Filter alleen op dienstritten in omloopplanning
    dienst_ritten_omloop = omloop_df[omloop_df['activiteit'] == 'dienst rit']
    
    for idx, row in dienst_ritten_omloop.iterrows():
        # Skip als starttijd NaT is
        if pd.isna(row['starttijd']):
            continue
        
        # Filter voor overeenkomstige rijen in de dienstregeling
        dienst_rows = dienst_df[
            (dienst_df['startlocatie'] == row['startlocatie']) &
            (dienst_df['eindlocatie'] == row['eindlocatie']) &
            (dienst_df['buslijn'] == row['buslijn'])
        ]
        
        for _, dienst_row in dienst_rows.iterrows():
            try:
                # Maak een vertrektijd datetime object
                vertrektijd = pd.to_datetime(f"{row['starttijd'].date()} {dienst_row['vertrektijd'].strip()}")
                
                # Controleer of de starttijd overeenkomt met de dienstregeling
                if vertrektijd == row['starttijd']:
                    omloop_df.at[idx, 'correct'] = True
                    break
            except Exception as e:
                # Optioneel: print of log de fout voor verdere analyse
                print(f"Fout in rij {idx}: {e}")
                continue

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
            continue

        if not omloop_rows.empty:
            dienst_df.at[idx, 'found_in_omloop'] = True

    return omloop_df, dienst_df

# Streamlit-app interface
st.title('Omloopplanning en Dienstregeling Analyse')

uploaded_file_1 = st.file_uploader("Upload Omloopplanning Bestand")
uploaded_file_2 = st.file_uploader("Upload Dienstregeling Bestand")

if uploaded_file_1 is not None and uploaded_file_2 is not None:
    # Gegevens laden
    df_omloopplanning, df_dienstregeling = load_data(uploaded_file_1, uploaded_file_2)

    # Voer de controle uit
    df_omloopplanning_checked, df_dienstregeling_checked = check_omloopplanning(df_omloopplanning, df_dienstregeling)

    # Resultaten weergeven
    st.subheader("Omloopplanning Resultaten")
    st.write(df_omloopplanning_checked)

    st.subheader("Dienstregeling Resultaten")
    st.write(df_dienstregeling_checked)
