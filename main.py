import streamlit as st
from google.oauth2 import service_account
from gsheetsdb import connect
import pandas as pd
import altair as alt
from datetime import date

with open("style.css") as css_file:
    st.markdown(f'<style>{css_file.read()}</style>', unsafe_allow_html=True)

# with open("./src/tablesort.js") as js_file:
#     st.markdown(f'<script>{js_file.read()}</script>', unsafe_allow_html=True)

status_order = ["LC", "NT", "VU", "EN", "CR", "EX", "DO", "DD", "NE"]

@st.cache_resource(ttl=6000)
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
print(df.columns)

df["Binomial_name"] = df["Scientific_name"].str.split().str[:2].str.join(" ")

# Sort the DataFrame by "Times_Appeared" column in descending order
df_sorted = df.sort_values("Air_Date", ascending=False).copy()

# Group the DataFrame by "Binomial_name" and select the first row for each group (highest "Times_Appeared" value)
last_appearance = df_sorted[['Binomial_name', 'Air_Date', 'Show', 'Episode', 'Times_Appeared']].groupby("Binomial_name").first()

# Group the DataFrame by "Binomial_name" and select the first row for each group (lowest "Times_Appeared" value)
first_appearance = df_sorted[['Binomial_name', 'Air_Date', 'Show', 'Episode', 'Times_Appeared']].groupby("Binomial_name").last()

# Merge the last appearance information back into the original DataFrame
merged_df = pd.merge(df, last_appearance[["Show", "Episode", "Air_Date", "Times_Appeared"]], on="Binomial_name", how="left").copy()

merged_df = merged_df.rename(columns={"Show_y": "Last Appeared In",
                                      "Episode_y": "Last Appeared In Episode",
                                      "Air_Date_y": "Last Appeared Date",
                                      "Times_Appeared_y": "# Times Featured"})


print(merged_df.columns)

# Merge the last appearance information back into the original DataFrame
merged_df_2 = pd.merge(merged_df, first_appearance[["Show", "Episode", "Air_Date"]], on="Binomial_name", how="left").copy()

merged_df_2 = merged_df_2.rename(columns={"Show": "First Appeared In",
                                      "Episode": "First Appeared In Episode",
                                      "Air_Date": "First Appeared Date"})

print(merged_df_2.columns)

unique_countries = sorted(merged_df_2["Country"].dropna().unique())

unique_families = sorted(merged_df_2["Family"].dropna().unique())

countries_selection = st.sidebar.multiselect(
    "Choose countries", unique_countries, []
)

families_selection = st.sidebar.multiselect(
    "Choose families", unique_families, ["Felidae", "Hominidae"]
)

# Create filter conditions based on user selections
country_filter = (merged_df_2["Country"].isin(countries_selection)) | (len(countries_selection) == 0)
family_filter = (merged_df_2["Family"].isin(families_selection)) | (len(families_selection) == 0)

# Apply filters to the DataFrame
filtered_df = merged_df_2[country_filter & family_filter]

status_css = {
    'LC': 'background-color: #4fc1ff; border: 2px solid #3a95d1; color: #ffffff; text-shadow: 0px 0px 1px #3283b5;',
    'NT': 'background-color: #67d62f; border: 2px solid #4cb517; color: #ffffff; text-shadow: 0px 0px 1px #47a315;',
    'VU': 'background-color: #edcb0b; border: 2px solid #dbae0d; color: #ffffff; text-shadow: 0px 0px 1px #c28b00;',
    'EN': 'background-color: #ff9123; border: 2px solid #c48e21; color: #ffffff; text-shadow: 0px 0px 1px #b38220;',
    'CR': 'background-color: #f03022; border: 2px solid #a8482b; color: #ffffff; text-shadow: 0px 0px 1px #7d3a25;',
    'NE': 'background-color: #ffffff; border: 2px solid #ebebeb; color: #000000; text-shadow: 0px 0px 2px #ffffff;',
    'DD': 'background-color: #ffffff; border: 2px solid #ebebeb; color: #000000; text-shadow: 0px 0px 2px #ffffff;',
    'DO': 'background-color: #9C826C; border: 2px solid #85552c; color: #ffffff; text-shadow: 0px 0px 2px #000000;',
    'EX': 'background-color: #363636; border: 2px solid #ff4647; color: #ffffff; text-shadow: 0px 0px 2px #000000;',
}

filtered_df['IUCN status'] = filtered_df['Species_status_original'].apply(lambda x: f'<span style="{status_css.get(x, "")}" class="ConservationStatusLabel">{x}</span>' if x is not None else "-")
filtered_df['Scientific name'] = filtered_df['Binomial_name'].apply(lambda x: f'<i>{x}</i>' if x is not None else "-")
filtered_df['Animal'] = filtered_df['Animal_name_original']
filtered_df['# Times Featured'] = pd.to_numeric(filtered_df['# Times Featured'], errors='coerce').fillna(0).astype(int)
filtered_df['Last Seen'] = filtered_df.apply(
    lambda row: f"{row['Last Appeared In']} ({row['Last Appeared Date'].strftime('%b %Y')})"
        if not pd.isnull(row['Last Appeared Date'])
        else "-",
    axis=1
)
filtered_df['First Seen'] = filtered_df.apply(
    lambda row: f"{row['First Appeared In']} ({row['First Appeared Date'].strftime('%b %Y')})"
        if not pd.isnull(row['First Appeared Date'])
        else "-",
    axis=1
)

columns = ["Animal", "Scientific name", "IUCN status", "# Times Featured"]

st.sidebar.write("Add optional columns:")
if st.sidebar.checkbox('First Seen'):
    columns.append("First Seen")
if st.sidebar.checkbox('Last Seen'):
    columns.append("Last Seen")

user_sort_selection = st.sidebar.radio(label="Sort by column:",
                                       options=("Alphabetical",
                                                "Scientific name",
                                                "IUCN status",
                                                "# Times Featured"))

sort_dict = {
    "Alphabetical": ["Animal"],
    "Scientific name": ["Scientific name"],
    "IUCN status": ["Species_status_original", "Animal"],
    "# Times Featured": ["# Times Featured", "Animal"]
}

ascending_order = {
    "Alphabetical": True,
    "Scientific name": True,
    "IUCN status": True,
    "# Times Featured": False
}

if len(families_selection) == 1:
    filtered_df_prep = filtered_df[columns + ["Species_status_original"]].drop_duplicates()
else:
    filtered_df_prep = filtered_df[["Family"] + columns + ["Species_status_original"]].drop_duplicates()

sort_columns = sort_dict.get(user_sort_selection, [])
if user_sort_selection == "IUCN status":
    filtered_df_unique = filtered_df_prep.sort_values(
        by=sort_columns,
        key=lambda x: pd.Categorical(x, categories=status_order, ordered=True),
        ascending=True
    )
else:
    filtered_df_unique = filtered_df_prep.sort_values(
        by=sort_columns,
        ascending=ascending_order.get(user_sort_selection, True)
    )

filtered_df_unique = filtered_df_unique[columns]
filtered_df_unique = filtered_df_unique.reset_index(drop=True)
filtered_df_unique.index = filtered_df_unique.index + 1

# Convert DataFrame to HTML
html_table = filtered_df_unique.to_html(escape=False, index=False, classes=['styled-table', 'table-sortable'])


st.markdown(f"<div class='species_table'>{html_table}</div>", unsafe_allow_html=True)
# Render the table with applied CSS styling

# st.table(filtered_df_unique)

# filtered_df_unique = filtered_df_unique.style.set_properties(**{'color': 'magenta',
#                                                                 'font-family': 'Fira Sans Condensed',
#                                                                 'font-size': '18px'})

# Display the DataFrame with interactive sorting enabled
# sorted_df = st.dataframe(filtered_df_unique)

# st.write(filtered_df_unique.to_html(), unsafe_allow_html=True)

df2 = filtered_df.groupby("Species_status_original").agg({
    "Binomial_name": "nunique"
}).reset_index()
df2.columns = ["Species_status_original", "Unique_BinomialName_Count"]

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
    y=alt.Y('Species_status_original', axis=alt.Axis(title='IUCN status', titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed"), sort=status_order),
    x=alt.X('Unique_BinomialName_Count', axis=alt.Axis(title='# Species', titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed", labelOverlap=True, tickMinStep=1)),
    color=alt.Color('Species_status_original', scale=alt.Scale(domain=list(status_colours.keys()), range=list(status_colours.values())), legend=alt.Legend(title='', labelFont="Fira Sans Condensed", labelLimit=0, symbolLimit=0, titleLimit=0, values=list(set(df2["Species_status_original"])))),
    stroke=alt.Stroke('Species_status_original', scale=alt.Scale(domain=list(status_colour_borders.keys()), range=list(status_colour_borders.values()))),
)

st.altair_chart(status_chart)
