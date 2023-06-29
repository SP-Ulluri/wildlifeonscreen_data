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
    'VU': 'background-color: #d6ba18; border: 2px solid #cfa715; color: #ffffff; text-shadow: 0px 0px 1px #c28b00;',
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
sheet_url_episodes = st.secrets["private_gsheets_url_episodes"]

df = get_data(sheet_url)
df_episodes = get_data(sheet_url_episodes)

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

# ------------- USER SELECTION ------------ #

unique_animals = sorted(raw_data["Animal"].dropna().unique())

animal_selection = st.sidebar.selectbox("Choose animal", unique_animals, unique_animals.index("Tiger"))

animal_data = raw_data.loc[raw_data["Animal"] == f"{animal_selection}"].copy().sort_values(by=["Air date"])

# ------------- RENDER DATA ------------ #

binomial_name = animal_data["Binomial name"].iloc[0]
species_status= animal_data["Species status"].iloc[0]
species_status_code = animal_data["Species status code"].iloc[0]
last_updated_at = animal_data["Species lock date"].sort_values().iloc[-1]  # Get last Species lock date
st.write(f'<div class="animal-header"><h1 style="padding:0px;">{animal_selection}</h1><span style="text-align:right;"><h6 style="opacity:0.5; padding:0px"><i>Updated: {last_updated_at.strftime("%d %b %Y")}</i></h6></span></div>', unsafe_allow_html=True)
st.write(f'<div class="animal-info-header"><h5 style="padding:0px;"><i>{binomial_name}</i></h5> <span style="{status_css.get(species_status_code, "")}" class="ConservationStatusLabelLarge">{species_status}</span></div>' if species_status is not None else "", unsafe_allow_html=True)

animal_data = animal_data.drop_duplicates().reset_index(drop=True)
animal_data.index += 1

# ------------- GALLERY ------------ #

st.markdown(f"<div class='section-banner'><h5>Image Gallery</h5></div>", unsafe_allow_html=True)

image_paths = []

for index, row in animal_data.iterrows():
    if row["Image 1"] is not None:
        show = row["Show"]
        episode = row["Episode"]
        air_date = row["Air date"].strftime("%-d %b %Y")
        air_year = row["Air date"].strftime("%Y")
        image = random.choice([value for value in [row["Image 1"], row["Image 2"], row["Image 3"]] if value is not None])
        path = f"https://ulluri.com/wildlifeonscreen/{show.replace(' ', '%20')}/{episode.replace(' ', '%20')}%20-%20{air_date.replace(' ', '%20')}/{image}.webp"
        image_paths.append([show, episode, air_year, path])

st.write('<div class="scroll-container">' + ''.join(f'<a href="{image[3]}"><img src="{image[3]}" alt="{image[0] + " - " + image[1] + " (" + image[2] + ")"}" width="250px">' for image in image_paths) + '</a></div>', unsafe_allow_html=True)

# ------------- MAP ------------ #

st.markdown(f"<div class='section-banner'><h5>Locations</h5></div>", unsafe_allow_html=True)
countries = alt.topo_feature(vega_data.world_110m.url, 'countries')

countries_map = alt.Chart(countries).mark_geoshape(
    fill='#353535',
    stroke='#686868',
    strokeWidth=0.3
).encode(
    tooltip=alt.value(None),
).project('naturalEarth1')

points_df = animal_data[(animal_data['Lon'].notna()) & (animal_data['Lat'].notna())].copy()
if not points_df.empty:
    points_df["Show"] = points_df.apply(lambda x: f'{x["Show"]} ({x["Air date"].strftime("%Y")})', axis=1)

    points = alt.Chart(points_df).mark_circle(opacity=0.5, color='#EDCB0D').encode(
        longitude='Lon:Q',
        latitude='Lat:Q',
        size=alt.value(50),
        tooltip=[alt.Tooltip('Country:N'), alt.Tooltip('Show:N')]
    )

    st.altair_chart(countries_map + points, use_container_width=True)
else:
    st.altair_chart(countries_map, use_container_width=True)

# ------------- TABLE ------------ #

st.markdown(f"<div class='section-banner' style='margin-top:-20px;'><h5>List of Appearances</h5></div>", unsafe_allow_html=True)

table_data = animal_data.copy()

table_headers = ["Show",
                 "Episode",
                 "Date",
                 "Watch now",
                 "Country",
                 "Continent"]

if len(table_data["Animal subspecies"].unique()) > 1:
    table_data.rename(columns={'Animal subspecies': 'Name'}, inplace=True)
    table_data["Scientific name"] = table_data["Scientific name"].map(lambda x: f"<i>{x}</i>" if x is not None else "")
    table_data["IUCN status"] = table_data["Subspecies status code"].map(lambda x: f'<span style="{status_css.get(x, "")}" class="ConservationStatusLabel">{x}</span>' if x is not None else "")
    table_headers.extend(["Name", "Scientific name", "IUCN status"])

table_data["Date"] = table_data["Air date"].apply(lambda x: x.strftime("%-d %b %Y"))

table_data = table_data.merge(df_episodes[["Show", "Episode", "Streaming_link"]], on=["Show", "Episode"], how="left")

table_data["Watch now"] = table_data["Streaming_link"].apply(lambda x: f"<a href='{x}'><img src={'https://iplayer-web.files.bbci.co.uk/page-builder/51.0.0/img/icons/favicon.ico' if (not pd.isna(x) and 'bbc' in x) else 'https://assets.nflxext.com/ffe/siteui/common/icons/nficon2016.ico'} width='15px'></a>" if x is not None else "")

user_sort_selection = st.sidebar.radio(label="Sort by:",
                                       options=tuple(table_headers))

if user_sort_selection == "IUCN status":
    table_data.sort_values(by="Subspecies status code", key=lambda x: pd.Categorical(x, categories=status_order, ordered=True), inplace=True)
elif user_sort_selection == "Date":
    table_data.sort_values(by="Air date", inplace=True)
else:
    table_data.sort_values(by=user_sort_selection, inplace=True)

html_table = table_data[table_headers].drop_duplicates().to_html(escape=False, index=False, classes=['styled-table', 'table-sortable'])

st.markdown(f"<div class='species_table'>{html_table}</div>", unsafe_allow_html=True)