import streamlit as st
from google.oauth2 import service_account
from gsheetsdb import connect
import pandas as pd
import altair as alt

@st.cache_resource(ttl=600)
def get_data(sheet_url):
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    conn = connect(credentials=credentials)

    # Fetch data from the Google Sheet.
    data = conn.execute(f'SELECT * FROM "{sheet_url}"')

    # Convert the data to a pandas DataFrame.
    df = pd.DataFrame(data)

    return df


sheet_url = st.secrets["private_gsheets_url"]

df = get_data(sheet_url)

df["Binomial_name"] = df["Scientific_name"].str.split().str[:2].str.join(" ")

# Sort the DataFrame by "Times_Appeared" column in descending order
df_sorted = df.sort_values("Air_date", ascending=False).copy()

# Group the DataFrame by "Scientific_name" and select the first row for each group (highest "Times_Appeared" value)
last_appearance = df_sorted[['Binomial_name', 'Air_date', 'Show', 'Episode']].groupby("Binomial_name").first()

# Merge the last appearance information back into the original DataFrame
merged_df = pd.merge(df, last_appearance[["Show", "Episode", "Air_date"]], on="Binomial_name", how="left")

merged_df = merged_df.rename(columns={"Show_y": "Last Appeared In",
                                      "Episode_y": "Last Appeared In Episode",
                                      "Air_date_y": "Last Appeared Date"})


unique_countries = sorted(merged_df["Country"].dropna().unique())
# print(unique_countries)

unique_families = sorted(merged_df["Family"].dropna().unique())
# print(unique_families)

# st.button('Hit me')
#
# st.radio('Radio', [1,2,3])
#
# st.select_slider('Slide to select', options=[1 ,'2'])
#
# user_text = st.text_input('Ask a question about the data')

countries_selection = st.multiselect(
    "Choose countries", unique_countries, []
)

families_selection = st.multiselect(
    "Choose families", unique_families, ["Felidae", "Canidae", "Hominidae"]
)

# Create filter conditions based on user selections
country_filter = (merged_df["Country"].isin(countries_selection)) | (len(countries_selection) == 0)
family_filter = (merged_df["Family"].isin(families_selection)) | (len(families_selection) == 0)

# Apply filters to the DataFrame
filtered_df = merged_df[country_filter & family_filter]

columns = ["Animal_name", "Binomial_name", "IUCN_status"]
if st.checkbox('Last Appeared In'):
    columns.append("Last Appeared In")

if st.checkbox('Last Appeared Date'):
    columns.append("Last Appeared Date")

# Display the filtered DataFrame as a table
if len(families_selection) == 1:
    filtered_df_unique = filtered_df[[columns]].drop_duplicates().sort_values(["Binomial_name"])
else:
    filtered_df_unique = filtered_df[["Family"] + columns].drop_duplicates().sort_values(["Family", "Binomial_name"])

filtered_df_unique = filtered_df_unique.reset_index(drop=True)
filtered_df_unique.index = filtered_df_unique.index + 1

# st.table(filtered_df_unique)

# Display the DataFrame with interactive sorting enabled
sorted_df = st.dataframe(filtered_df_unique)

df2 = filtered_df.groupby("IUCN_status").agg({
    "Binomial_name": "nunique"
}).reset_index()
df2.columns = ["IUCN_status", "Unique_BinomialName_Count"]

status_order = ["LC", "NT", "VU", "EN", "CR", "EX", "DO", "DD", "NE"]

status_colours = {
    "LC": "#63c5ff",
    "NT": "#7af054",
    "VU": "#e5cb50",
    "EN": "#ffa759",
    "CR": "#f65f54",
    "DO": "#9C826C",
    "DD": "#b9b9b9",
    "NE": "#b9b9b9",
    "EX": "#363636"
}

status_colour_borders = {
    "LC": "#2db6ff",
    "NT": "#3eb800",
    "VU": "#d1a300",
    "EN": "#cd8900",
    "CR": "#b3310b",
    "DO": "#85552c",
    "DD": "#979797",
    "NE": "#979797",
    "EX": "#ff4647"
}

status_chart = alt.Chart(df2).mark_bar(strokeWidth=2.5).encode(
    y=alt.Y('IUCN_status', axis=alt.Axis(title='IUCN status'), sort=status_order),
    x=alt.X('Unique_BinomialName_Count', axis=alt.Axis(title='# Species', labelOverlap=True, tickMinStep=1)),
    color=alt.Color('IUCN_status', scale=alt.Scale(domain=list(status_colours.keys()), range=list(status_colours.values())), legend=alt.Legend(title='', labelLimit=0, symbolLimit=0, titleLimit=0, values=list(set(df2["IUCN_status"])))),
    stroke=alt.Stroke('IUCN_status', scale=alt.Scale(domain=list(status_colour_borders.keys()), range=list(status_colour_borders.values()))),
)

st.altair_chart(status_chart)
