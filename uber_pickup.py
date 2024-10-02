# Importeren van benodigde libraries
import streamlit as st
import pandas as pd
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

#############################################

# Inladen van data
df_omloopplanning, df_dienstregeling = load_data()

# Converteer tijd kolommen naar datetime objecten voor makkelijke bewerking
df_omloopplanning['starttijd'] = pd.to_datetime(df_omloopplanning['starttijd datum'], errors='coerce')
df_omloopplanning['eindtijd'] = pd.to_datetime(df_omloopplanning['eindtijd datum'], errors='coerce')

# Voer de controle uit
df_omloopplanning, df_dienstregeling = check_omloopplanning(df_omloopplanning, df_dienstregeling)

# Titel van de Streamlit App
st.title('Omloopplanning Controle Systeem')

# Deel 1: Resultaten van omloopplanning controleren
st.header('Resultaten van Omloopplanning Controle')
filtered_df = df_omloopplanning[df_omloopplanning['activiteit'] == 'dienst rit']
false_count = filtered_df['correct'].value_counts().get(False, 0)
st.write(f"Aantal onjuiste dienstritten in omloopplanning: {false_count}")

if false_count > 0:
    false_rows = filtered_df[filtered_df['correct'] == False]
    st.subheader("Onjuiste dienstritten in omloopplanning:")
    st.dataframe(false_rows[['startlocatie', 'eindlocatie', 'starttijd', 'eindtijd', 'buslijn', 'correct']])

# Deel 2: Resultaten van dienstregeling controleren
st.header('Resultaten van Dienstregeling Controle')
not_found_count = df_dienstregeling['found_in_omloop'].value_counts().get(False, 0)
st.write(f"Aantal dienstritten in dienstregeling die niet in omloopplanning zijn gevonden: {not_found_count}")

if not_found_count > 0:
    not_found_rows = df_dienstregeling[df_dienstregeling['found_in_omloop'] == False]
    st.subheader("Dienstritten in dienstregeling die niet in de omloopplanning zijn gevonden:")
    st.dataframe(not_found_rows[['startlocatie', 'eindlocatie', 'vertrektijd', 'buslijn']])

# Interactieve tabellen tonen
st.subheader('Omloopplanning Data (Eerste 5 rijen)')
st.dataframe(df_omloopplanning.head())

st.subheader('Dienstregeling Data (Eerste 5 rijen)')
st.dataframe(df_dienstregeling.head())
