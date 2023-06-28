import streamlit as st
from google.oauth2 import service_account
from gsheetsdb import connect
import pandas as pd
import altair as alt
from vega_datasets import data as vega_data
import iso3166
import random

random.seed(42)

with open("style.css") as css_file:
    st.markdown(f'<style>{css_file.read()}</style>', unsafe_allow_html=True)

# with open("./src/tablesort.js") as js_file:
#     st.markdown(f'<script>{js_file.read()}</script>', unsafe_allow_html=True)

status_order = ["LC", "NT", "VU", "EN", "CR", "EX", "DO", "DD", "NE"]

status_code_labels = {
    "LC": "Least Concern",
    "NT": "Near Threatened",
    "VU": "Vulnerable",
    "EN": "Endangered",
    "CR": "Critically Endangered",
    "DO": "Domesticated",
    "DD": "Data Deficient",
    "NE": "Not Evaluated",
    "EX": "Extinct"
}

status_css = {
    'LC': 'background-color: #4fc1ff; border: 2px solid #3a95d1; color: #ffffff; text-shadow: 0px 0px 1px #3283b5;',
    'NT': 'background-color: #67d62f; border: 2px solid #4cb517; color: #ffffff; text-shadow: 0px 0px 1px #47a315;',
    'VU': 'background-color: #edcb0b; border: 2px solid #dbae0d; color: #ffffff; text-shadow: 0px 0px 1px #c28b00;',
    'EN': 'background-color: #ff9123; border: 2px solid #c48e21; color: #ffffff; text-shadow: 0px 0px 1px #b38220;',
    'CR': 'background-color: #f03022; border: 2px solid #a8482b; color: #ffffff; text-shadow: 0px 0px 1px #7d3a25;',
    'NE': 'background-color: #ffffff; border: 2px solid #ebebeb; color: #000000; text-shadow: 0px 0px 2px #ffffff;',
    'DD': 'background-color: #ffffff; border: 2px solid #ebebeb; color: #000000; text-shadow: 0px 0px 2px #ffffff;',
    'DO': 'background-color: #9C826C; border: 2px solid #85552c; color: #ffffff; text-shadow: 0px 0px 2px #444444;',
    'EX': 'background-color: #363636; border: 2px solid #ff4647; color: #ffffff; text-shadow: 0px 0px 2px #000000;',
}

@st.cache_resource(ttl=6000)
def get_data(sheet_url):
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    conn = connect(credentials=credentials)

    # Fetch data from the Google Sheet.
    raw = conn.execute(f'SELECT * FROM "{sheet_url}"')

    # Convert the data to a pandas DataFrame.
    df = pd.DataFrame(raw)

    return df


sheet_url = st.secrets["private_gsheets_url"]

df = get_data(sheet_url)

initial_cols = ["Appearance_number",
                "Coappearance_number",
                "Other_animals",
                "Show",
                "Episode",
                "Air_date",
                "Is_New",
                "ID",
                "Image_1",
                "Image_2",
                "Image_3",
                # "Sequence_number",
                "Animal_name",
                "Animal_name_original",
                "Scientific_name",
                "Species_status",
                "Species_status_original",
                "Class",
                "Family",
                "Species_lock_date",
                "Summary",
                "Location",
                "Country",
                "Country_code",
                "Continent",
                # "Scientific_advisor",
                "Notes",
                # "Link_1",
                # "Link_2",
                # "Link_3",
                "Lat",
                "Lon",
                # "Sentence_start",
                # "Sentence_end"
                ]

raw_data = df[initial_cols].copy()

# ------------- PRE-PROCESSING ------------ #

# Renaming columns
column_mapping = {col: col.replace("_", " ") for col in raw_data.columns}
raw_data.rename(columns=column_mapping, inplace=True)

raw_data.rename(columns={'Species status': 'Subspecies status code',
                     'Species status original': 'Species status code',
                     'Animal name original': 'Animal',
                     'Animal name': 'Animal subspecies'
                         },
                inplace=True)

# Get binomial name where scientific name contains trinomial name
raw_data["Binomial name"] = raw_data["Scientific name"].str.split().str[:2].str.join(" ")

# Map species status codes to full status names
raw_data["Species status"] = raw_data["Species status code"].map(status_code_labels)
raw_data["Subspecies status"] = raw_data["Subspecies status code"].map(status_code_labels)

# Get ISO3166 ID using country code
country_mapping = {c.alpha3: int(c.numeric.lstrip('0')) for c in iso3166.countries}
raw_data["ISO3166 ID"] = raw_data["Country code"].replace(country_mapping)

# Remove indeterminate species
raw_data = raw_data[~raw_data["Animal"].apply(lambda x: isinstance(x, str) and "sp." in x)]

# print(raw_data.loc[raw_data["Animal"] == "Leopard", ["Animal", "Animal subspecies", "Species status", "Subspecies status", "Scientific name"]].drop_duplicates().head())

# ------------- OLD CODE ------------ #


# Get binomial name where scientific name contains trinomial name
df["Binomial_name"] = df["Scientific_name"].str.split().str[:2].str.join(" ")

# Sort the DataFrame by "Air_date" column in descending order
df_sorted = df.sort_values("Air_date", ascending=False).copy()

# Group the DataFrame by "Binomial_name" and select the first row for each group (highest "Times_Appeared" value)
last_appearance = df_sorted.groupby("Binomial_name").first()

# Group the DataFrame by "Binomial_name" and select the first row for each group (lowest "Times_Appeared" value)
first_appearance = df_sorted.groupby("Binomial_name").last()

# Merge the last appearance information back into the original DataFrame
merged_df = pd.merge(df, last_appearance[["Show", "Episode", "Air_date", "Appearance_number"]],
                     on="Binomial_name", how="left").copy()
merged_df.rename(columns={"Show_y": "Last Appeared In",
                          "Episode_y": "Last Appeared In Episode",
                          "Air_date_y": "Last Appeared Date",
                          "Appearance_number_y": "# Times Featured"}, inplace=True)

# Merge the first appearance information back into the original DataFrame
merged_df = pd.merge(merged_df, first_appearance[["Show", "Episode", "Air_date"]],
                     on="Binomial_name", how="left").copy()
merged_df.rename(columns={"Show": "First Appeared In",
                          "Episode": "First Appeared In Episode",
                          "Air_date": "First Appeared Date"}, inplace=True)


# Filter based on user selections
unique_continents = sorted(merged_df["Continent"].dropna().unique())
unique_countries = sorted(merged_df["Country"].dropna().unique())
unique_classes = sorted(merged_df["Class"].dropna().unique())
unique_families = sorted(merged_df["Family"].dropna().unique())

# Apply continent filter to country selection options
continents_selection = st.sidebar.multiselect("Filter by continent", unique_continents, [])
if continents_selection:
    unique_countries = sorted(merged_df.loc[merged_df["Continent"].isin(continents_selection), "Country"].dropna().unique())

countries_selection = st.sidebar.multiselect("Filter by country", unique_countries, [])

# Apply class filter to family selection options
class_selection = st.sidebar.multiselect("Filter by taxon classes", unique_classes, ["Mammalia"])
if class_selection:
    unique_families = sorted(merged_df.loc[merged_df["Class"].isin(class_selection), "Family"].dropna().unique())

families_selection = st.sidebar.multiselect("Filter by taxon families", unique_families, [])

# Create filter conditions based on user selections
continents_filter = merged_df["Continent"].isin(continents_selection) | (len(continents_selection) == 0)
countries_filter = (merged_df["Country"].isin(countries_selection)) | (len(countries_selection) == 0)
class_filter = (merged_df["Class"].isin(class_selection)) | (len(class_selection) == 0)
family_filter = (merged_df["Family"].isin(families_selection)) | (len(families_selection) == 0)

filtered_df = merged_df[continents_filter & countries_filter & class_filter & family_filter].copy()

status_css = {
    'LC': 'background-color: #4fc1ff; border: 2px solid #3a95d1; color: #ffffff; text-shadow: 0px 0px 1px #3283b5;',
    'NT': 'background-color: #67d62f; border: 2px solid #4cb517; color: #ffffff; text-shadow: 0px 0px 1px #47a315;',
    'VU': 'background-color: #edcb0b; border: 2px solid #dbae0d; color: #ffffff; text-shadow: 0px 0px 1px #c28b00;',
    'EN': 'background-color: #ff9123; border: 2px solid #c48e21; color: #ffffff; text-shadow: 0px 0px 1px #b38220;',
    'CR': 'background-color: #f03022; border: 2px solid #a8482b; color: #ffffff; text-shadow: 0px 0px 1px #7d3a25;',
    'NE': 'background-color: #ffffff; border: 2px solid #ebebeb; color: #000000; text-shadow: 0px 0px 2px #ffffff;',
    'DD': 'background-color: #ffffff; border: 2px solid #ebebeb; color: #000000; text-shadow: 0px 0px 2px #ffffff;',
    'DO': 'background-color: #9C826C; border: 2px solid #85552c; color: #ffffff; text-shadow: 0px 0px 2px #444444;',
    'EX': 'background-color: #363636; border: 2px solid #ff4647; color: #ffffff; text-shadow: 0px 0px 2px #000000;',
}

filtered_df = filtered_df[~filtered_df["Animal_name_original"].apply(lambda x: isinstance(x, str) and "sp." in x)]
filtered_df['IUCN status'] = filtered_df['Species_status_original'].map(lambda x: f'<span style="{status_css.get(x, "")}" class="ConservationStatusLabel">{x}</span>' if x is not None else "-")
filtered_df['Scientific name'] = filtered_df['Binomial_name'].map(lambda x: f'<i>{x}</i>' if x is not None else "-")
filtered_df['Animal'] = filtered_df['Animal_name_original']
filtered_df['# Times Featured'] = pd.to_numeric(filtered_df['# Times Featured'], errors='coerce').fillna(0).astype(int)
filtered_df['Last Seen'] = filtered_df.apply(
    lambda row: f"{row['Last Appeared In']} ({row['Last Appeared Date'].strftime('%Y')})"
    if not pd.isnull(row['Last Appeared Date'])
    else "-",
    axis=1
)
filtered_df['First Seen'] = filtered_df.apply(
    lambda row: f"{row['First Appeared In']} ({row['First Appeared Date'].strftime('%Y')})"
    if not pd.isnull(row['First Appeared Date'])
    else "-",
    axis=1
)

columns = ["Animal", "Scientific name", "IUCN status", "# Times Featured"]

if st.sidebar.checkbox('First Seen'):
    columns.append("First Seen")
if st.sidebar.checkbox('Last Seen'):
    columns.append("Last Seen")

user_sort_selection = st.sidebar.radio(label="Sort by column:",
                                       options=("Alphabetical", "Scientific name", "IUCN status", "# Times Featured"))

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

sort_columns = sort_dict.get(user_sort_selection, [])

if len(families_selection) == 1:
    filtered_df_prep = filtered_df[columns + ["Species_status_original"]].drop_duplicates()
else:
    filtered_df_prep = filtered_df[["Family"] + columns + ["Species_status_original"]].drop_duplicates()

if user_sort_selection == "IUCN status":
    filtered_df_unique = filtered_df_prep.sort_values(
        by=sort_columns,
        key=lambda x: pd.Categorical(x, categories=status_order, ordered=True),
        ascending=True
    )
else:
    filtered_df_unique = filtered_df_prep.sort_values(
        by=sort_columns,
        ascending=ascending_order.get(user_sort_selection, True))

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
    x=alt.X('Unique_BinomialName_Count', axis=alt.Axis(title='# Species', titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed", labelOverlap=True, tickMinStep=1)),
    y=alt.Y('Species_status_original', axis=alt.Axis(title='IUCN status', titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed"), sort=status_order),
    color=alt.Color('Species_status_original', scale=alt.Scale(domain=list(status_colours.keys()), range=list(status_colours.values())), legend=alt.Legend(title='', labelFont="Fira Sans Condensed", labelLimit=0, symbolLimit=0, titleLimit=0, values=list(set(df2["Species_status_original"])))),
    # stroke=alt.Stroke('Species_status_original', scale=alt.Scale(domain=list(status_colour_borders.keys()), range=list(status_colour_borders.values()))),
)

st.altair_chart(status_chart)

df3 = filtered_df.groupby(["Country"]).agg({
    "Binomial_name": "nunique"
}).reset_index()
df3.columns = ["Country", "NumSpecies"]

# Sort the DataFrame based on "Unique_BinomialName_Count" in descending order
sorted_df3 = df3.sort_values(by="NumSpecies", ascending=False)

# Reset the index and create a new column with row numbers
sorted_df3['RowNumber'] = range(1, len(sorted_df3) + 1)
sorted_df3.reset_index(drop=True, inplace=True)

# Add country code column
sorted_df3['id'] = [None] * len(sorted_df3)  # Initialize the column with None

# for i, country in enumerate(df["Country"]):
#     if country is None:
#         pass
#     else:
#         try:
#             country_obj = iso3166.countries.get(country)
#             if country != country_obj.name:
#                 print(country, country_obj.name, int(country_obj.numeric.lstrip('0')))
#         except KeyError:
#             pass

# for c in iso3166.countries:
#     print(c)

country_mapping = {
    "Russia": 643,
    "Tanzania": 834,
    "Republic of the Congo": 178,
    "Democratic Republic of the Congo": 180,
    "Ivory Coast": 384,
    "USA": 840,
    "UK": 826,
    "Falkland Islands": 238,
    "Central African Republic": 140,
    "South Sandwich Islands": 239,
    "Viet Nam": 704,
    "United Arab Emirates": 784,
    "Türkiye": 792,
    "Syria": 760,
    "Micronesia": 583,
    "Laos": 418,
    "South Korea": 410,
    "Bolivia": 68,
    "French Guiana": 254
}

# Iterate over country names and add country code if found
for i, country in enumerate(sorted_df3['Country']):
    if country in country_mapping:
        sorted_df3.loc[i, 'id'] = country_mapping[country]
        sorted_df3.loc[i, 'Country_Name'] = country
    else:
        try:
            country_obj = iso3166.countries.get(country)
            if country != country_obj.name:
                print(country, country_obj.name, int(country_obj.numeric.lstrip('0')))
            if country_obj:
                sorted_df3.loc[i, 'id'] = int(country_obj.numeric.lstrip('0'))
                sorted_df3.loc[i, 'Country_Name'] = country_obj.name
        except KeyError:
            pass

countries = alt.topo_feature(vega_data.world_110m.url, 'countries')

n = 10
colour_scheme = "goldgreen"
# Create two columns for the charts
col1, col2 = st.columns([0.3, 0.7])

# Chart 1 - Bar Chart
with col1:
    country_chart = alt.Chart(sorted_df3.head(n)).mark_bar().encode(
        y=alt.Y('Country', axis=alt.Axis(title=f'Top {n} countries', titleFont="Fira Sans Condensed", labelFontSize=12, labelFont="Fira Sans Condensed", labelOverlap=True), sort="-x"),
        x=alt.X('NumSpecies', axis=alt.Axis(title='# Species', titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed", labelOverlap=True, tickMinStep=1)),
        color=alt.Color('RowNumber', scale=alt.Scale(scheme=colour_scheme), sort="descending", legend=None),
        tooltip=[
            alt.Tooltip('Country:N'),
            alt.Tooltip('NumSpecies:Q', title='# Species')
        ]
    ).properties(height=300)
    st.altair_chart(country_chart, use_container_width=True)

# Chart 2 - Choropleth Map
with col2:
    country_map = alt.Chart(countries).mark_geoshape(
        stroke='#353535',
        strokeWidth=0.3
    ).transform_lookup(
        lookup='id',
        from_=alt.LookupData(data=sorted_df3, key='id', fields=['NumSpecies', 'Country'])
    ).transform_calculate(
        NumSpecies='isValid(datum.NumSpecies) ? datum.NumSpecies : -1',
    ).encode(
        color=alt.condition('datum.NumSpecies > 0',
                            alt.Color('NumSpecies:Q', scale=alt.Scale(scheme=colour_scheme), sort="ascending", legend=None),
                            alt.value('#242424')
                            ),
        tooltip=[
            alt.Tooltip('Country:N'),
            alt.Tooltip('NumSpecies:Q', title='# Species')
        ]
    ).project(
        "naturalEarth1"
        # "orthographic"
        # "equalEarth"
    ).properties(height=250)

    st.altair_chart(country_map, use_container_width=True)

# https://vega.github.io/vega/docs/schemes/

# df4 = filtered_df.groupby("Class").agg({
#     "Binomial_name": "nunique"
# }).reset_index()
# df4.columns = ["Class", "Unique_BinomialName_Count"]
#
# # Sort the DataFrame based on "Unique_BinomialName_Count" in descending order
# sorted_df4 = df4.sort_values(by="Unique_BinomialName_Count", ascending=False)
#
# # Reset the index and create a new column with row numbers
# sorted_df4['RowNumber'] = range(1, len(sorted_df4) + 1)
# sorted_df4.reset_index(drop=True, inplace=True)
#
# class_chart = st.altair_chart(alt.Chart(sorted_df4).mark_bar().encode(
#     y=alt.Y('Class', axis=alt.Axis(title='Taxon Class', titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed", labelOverlap=True),
#             sort="-x"),
#     x=alt.X('Unique_BinomialName_Count',
#             axis=alt.Axis(title='# Species', titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed",
#                           labelOverlap=True, tickMinStep=1)),
#     color=alt.Color('RowNumber', scale=alt.Scale(scheme='plasma'), sort="descending", legend=None)
# ).properties(height=500))
