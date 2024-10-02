import streamlit as st
import pandas as pd
import warnings

warnings.filterwarnings('ignore')

def load_data():
    df_omloopplanning = pd.read_excel('omloopplanning.xlsx', engine='openpyxl')
    df_dienstregeling = pd.read_excel('Connexxion data - 2024-2025.xlsx', engine='openpyxl')
    return df_omloopplanning, df_dienstregeling

def check_omloopplanning(omloop_df, dienst_df):
    omloop_df['correct'] = False
    dienst_ritten_omloop = omloop_df[omloop_df['activiteit'] == 'dienst rit']
    
    for idx, row in dienst_ritten_omloop.iterrows():
        dienst_rows = dienst_df[
            (dienst_df['startlocatie'] == row['startlocatie']) &
            (dienst_df['eindlocatie'] == row['eindlocatie']) &
            (dienst_df['buslijn'] == row['buslijn'])
        ]
        
        for _, dienst_row in dienst_rows.iterrows():
            if pd.isna(row['starttijd']):
                continue
            
            vertrektijd = pd.to_datetime(f"{row['starttijd'].date()} {dienst_row['vertrektijd'].strip()}")
            
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
            continue

        if not omloop_rows.empty:
            dienst_df.at[idx, 'found_in_omloop'] = True

    return omloop_df, dienst_df

st.title('Omloopplanning en Dienstregeling')

df_omloopplanning, df_dienstregeling = load_data()

df_omloopplanning['starttijd'] = pd.to_datetime(df_omloopplanning['starttijd datum'], errors='coerce')
df_omloopplanning['eindtijd'] = pd.to_datetime(df_omloopplanning['eindtijd datum'], errors='coerce')

df_omloopplanning, df_dienstregeling = check_omloopplanning(df_omloopplanning, df_dienstregeling)

# Gebruik CSS om de totale breedte van de DataFrames aan te passen
st.markdown(
    """
    <style>
    .dataframe-container {
        display: block;
        overflow-x: auto;
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True
)

# Veronderstel dat df_omloopplanning al bestaat. Hier wordt aangenomen dat deze dataframe beschikbaar is.
# df_omloopplanning = ...

st.title('Resultaten van Omloopplanning Controle')

# Filter om alleen rijen met 'dienst rit' te behouden
filtered_df = df_omloopplanning[df_omloopplanning['activiteit'] == 'dienst rit']

# Tel het aantal onjuiste dienstritten
false_count = filtered_df['correct'].value_counts().get(False, 0)
st.write(f"Aantal onjuiste dienstritten in omloopplanning: {false_count}")

if false_count > 0:
    false_rows = filtered_df[filtered_df['correct'] == False]
    st.write("Onjuiste dienstritten in omloopplanning:")
    st.dataframe(false_rows[['startlocatie', 'eindlocatie', 'starttijd', 'eindtijd', 'buslijn', 'correct']])
    st.dataframe(false_rows[['startlocatie', 'eindlocatie', 'starttijd', 'eindtijd', 'buslijn', 'correct']], use_container_width=True)
