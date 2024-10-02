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

# Inladen van data
df_omloopplanning, df_dienstregeling = load_data()

# Converteer tijd kolommen naar datetime objecten voor makkelijke bewerking
df_omloopplanning['starttijd'] = pd.to_datetime(df_omloopplanning['starttijd datum'], errors='coerce')
df_omloopplanning['eindtijd'] = pd.to_datetime(df_omloopplanning['eindtijd datum'], errors='coerce')

# Voer de controle uit
df_omloopplanning, df_dienstregeling = check_omloopplanning(df_omloopplanning, df_dienstregeling)

# Nieuwe kolom 'duur' toevoegen die het verschil tussen eindtijd en starttijd aangeeft
df_omloopplanning['duur'] = df_omloopplanning['eindtijd'] - df_omloopplanning['starttijd']

# De kolom 'duur' converteren naar minuten
df_omloopplanning['duur_minuten'] = df_omloopplanning['duur'].dt.total_seconds() / 60

# De kolom 'duur_minuten' converteren naar uren
df_omloopplanning['duur_uren'] = df_omloopplanning['duur_minuten'] / 60

# Totale gebruikte kilowatturen (kWh) berekenen en opslaan in een nieuwe kolom 'gebruikt_kW'
df_omloopplanning['gebruikt_kW'] = df_omloopplanning['duur_uren'] * df_omloopplanning['energieverbruik']

# Berekeningen voor de batterij en SOC
max_batt_capa = 300  # kW
SOC_start = 0.9  # factor
SOC_min = 0.1  # factor
batterijslijtage = 0.85  # Afhankelijk van de leeftijd van de bus is dat zo’n 85%-95% van de maximale capaciteit 
SOH = max_batt_capa * batterijslijtage  # De SOH is de maximale capaciteit van een specifieke bus

SOC_ochtend = SOH * SOC_start  # De SOC geeft aan hoeveel procent de bus nog geladen is. 100% is daarbij gelijk aan de SOH van de bus.
SOC_minimum = SOH * SOC_min  # De veiligheidsmarge van 10% heeft ook betrekking op de SOH

# DataFrame maken voor batterijparameters
data = {
    'Parameter': ['Max Batterij Capaciteit', 'SOC Start', 'SOC Minimum', 'Batterij Slijtage', 'SOH', 'SOC Ochtend', 'SOC Minimum'],
    'Waarde': [max_batt_capa, SOC_start, SOC_min, batterijslijtage, SOH, SOC_ochtend, SOC_minimum],
    'Eenheid': ['kW', 'Factor', 'Factor', 'Factor', 'kW (MBC * BS)', 'kW (SOH * SOC S)', 'kW (SOH * SOC M)']
}

df_battery = pd.DataFrame(data)

# Initialiseren van de kolommen voor SOC
df_omloopplanning['SOC_beginrit'] = 0.0
df_omloopplanning['SOC_eindrit'] = 0.0

# Berekenen van SOC_beginrit en SOC_eindrit per rit
huidige_omloop = None
huidige_SOC = SOC_ochtend

for index, row in df_omloopplanning.iterrows():
    if row['omloop nummer'] != huidige_omloop:
        huidige_omloop = row['omloop nummer']
        huidige_SOC = SOC_ochtend
    
    # SOC_beginrit instellen
    df_omloopplanning.at[index, 'SOC_beginrit'] = huidige_SOC
    
    # SOC_eindrit berekenen
    huidige_SOC -= row['gebruikt_kW']
    df_omloopplanning.at[index, 'SOC_eindrit'] = huidige_SOC

    # Controle of nodig is
    if huidige_SOC < SOC_minimum:
        st.warning(f"Waarschuwing: SOC onder de minimum veiligheidsmarge voor omloop nummer {huidige_omloop} bij index {index}.")

# Toevoegen van nieuwe kolom die aangeeft of SOC_eindrit boven SOC_minimum is
df_omloopplanning['SOC_above_min'] = df_omloopplanning['SOC_eindrit'] > SOC_minimum

# Berekenen van de laagste SOC_eindrit per omloopnummer
min_SOC_per_omloopnummer = df_omloopplanning.groupby('omloop nummer')['SOC_eindrit'].min().reset_index()
min_SOC_per_omloopnummer.columns = ['omloop nummer', 'min_SOC_eindrit']

# Haal de unieke waarden uit de kolom 'activiteit'
unieke_waarden_activiteit = df_omloopplanning['activiteit'].unique()

# Filter de rijen waarbij 'activiteit' gelijk is aan 'opladen'
opladen_df = df_omloopplanning[df_omloopplanning['activiteit'] == 'opladen']

if opladen_df.empty:
    opladen_message = "Geen rijen gevonden waarbij de 'activiteit' gelijk is aan 'opladen'."
else:
    # Voeg een nieuwe kolom toe die aangeeft of de 'duur_minuten' groter is dan 15
    opladen_df['lang_genoeg_opgeladen'] = opladen_df['duur_minuten'] > 15

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

# Resultaten van nieuwe berekeningen weergeven
st.subheader('Berekeningsresultaten')
st.write("Energieverbruik en duur van elke dienst:")
st.dataframe(df_omloopplanning[['starttijd', 'eindtijd', 'duur_uren', 'energieverbruik', 'gebruikt_kW', 'omloop nummer']].head())

# Batterijparameters weergeven
st.subheader('Batterijparameters en SOC')
st.dataframe(df_battery)

# SOC en veiligheid
st.subheader('SOC Berekeningen')
st.write("Staat van de batterijlading bij het begin en het einde van elke rit:")
st.dataframe(df_omloopplanning[['omloop nummer', 'starttijd', 'eindtijd', 'duur_uren', 'energieverbruik', 'gebruikt_kW', 'SOC_beginrit', 'SOC_eindrit', 'SOC_above_min']].head())

# Laagste SOC_eindrit per omloopnummer
st.subheader('Laagste SOC_eindrit per Omloopnummer')
st.dataframe(min_SOC_per_omloopnummer)

# Unieke waarden van activiteit
st.subheader('Unieke Waarden van Activiteit')
st.write(", ".join(unieke_waarden_activiteit))

# Opladen activiteit
st.subheader('Opladen Activiteit')
if opladen_df.empty:
    st.write(opladen_message)
else:
    st.write("Rijen waarbij de 'activiteit' gelijk is aan 'opladen':")
    st.dataframe(opladen_df[['activiteit', 'energieverbruik', 'duur_minuten', 'SOC_above_min', 'lang_genoeg_opgeladen']])

    # Filter de rijen waarbij 'lang_genoeg_opgeladen' False is
    niet_lang_genoeg_opgeladen_df = opladen_df[opladen_df['lang_genoeg_opgeladen'] == False]
    
    st.write("Rijen waarin 'lang_genoeg_opgeladen' False is:")
    st.dataframe(niet_lang_genoeg_opgeladen_df[['activiteit', 'energieverbruik', 'duur_minuten', 'SOC_above_min', 'lang_genoeg_opgeladen']])
