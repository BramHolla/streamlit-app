# Importeren van benodigde libraries
import pandas as pd
import streamlit as st
import warnings

# Waarschuwingen negeren
warnings.filterwarnings('ignore')

# Functie om data in te laden
def load_data():
    # Hardcode de bestandslocaties
    omloop_file = 'omloopplanning.xlsx'
    dienst_file = 'Connexxion data - 2024-2025.xlsx'
    
    df_omloopplanning = pd.read_excel(omloop_file, engine='openpyxl')
    df_dienstregeling = pd.read_excel(dienst_file, engine='openpyxl')
    return df_omloopplanning, df_dienstregeling

def check_omloopplanning(omloop_df, dienst_df):
    omloop_df['correct'] = False

    # Filter alleen op dienstritten in omloopplanning
    dienst_ritten_omloop = omloop_df[omloop_df['activiteit'] == 'dienst rit']
    
    for idx, row in dienst_ritten_omloop.iterrows():
        dienst_rows = dienst_df[
            (dienst_df['startlocatie'] == row['startlocatie']) &
            (dienst_df['eindlocatie'] == row['eindlocatie']) &
            (dienst_df['buslijn'] == row['buslijn'])
        ]
        
        for _, dienst_row in dienst_rows.iterrows():
            if pd.isna(row['starttijd']):
                st.warning(f"Skipping row {idx} because starttijd is NaT")
                continue
            
            try:
                vertrektijd = pd.to_datetime(f"{row['starttijd'].date()} {dienst_row['vertrektijd'].strip()}")
            except Exception as e:
                st.error(f"Error processing starttijd for row {idx}: {e}")
                continue
            
            if vertrektijd == row['starttijd']:
                omloop_df.at[idx, 'correct'] = True
                break

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
            st.warning(f"Error in row {idx}: {str(e)}")
            continue

        if not omloop_rows.empty:
            dienst_df.at[idx, 'found_in_omloop'] = True

    return omloop_df, dienst_df

def main():
    st.title("Omloopplanning en Dienstregeling Controle")
    omloop_df, dienst_df = load_data()

    if omloop_df is not None and dienst_df is not None:
        omloop_result, dienst_result = check_omloopplanning(omloop_df, dienst_df)

        st.subheader("Omloopplanning Resultaten")
        st.dataframe(omloop_result)

        st.subheader("Dienstregeling Resultaten")
        st.dataframe(dienst_result)
    else:
        st.info("Zorg ervoor dat de bestanden correct zijn ingeladen.")

if __name__ == "__main__":
    main()
