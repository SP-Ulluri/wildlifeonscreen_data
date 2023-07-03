import streamlit as st
from google.oauth2 import service_account
from gsheetsdb import connect
import pandas as pd
import altair as alt
from vega_datasets import data as vega_data
import iso3166
import random
from datetime import datetime as dt

random.seed(42)

sample_animal = "African bush elephant"

with open("style.css") as css_file:
    st.markdown(f'<style>{css_file.read()}</style>', unsafe_allow_html=True)

st.write("""<br>""", unsafe_allow_html=True)

status_order = ["Least Concern",
                "Near Threatened",
                "Vulnerable",
                "Endangered",
                "Critically Endangered",
                "Extinct",
                "Domesticated",
                "Data Deficient",
                "Not Evaluated"]

status_colours = {
    "Least Concern": "#63c5ff",
    "Near Threatened": "#7af054",
    "Vulnerable": "#e5cb50",
    "Endangered": "#ffa759",
    "Critically Endangered": "#f65f54",
    "Domesticated": "#9C826C",
    "Data Deficient": "#b9b9b9",
    "Not Evaluated": "#b9b9b9",
    "Extinct": "#363636"
}

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
    'Least Concern': 'background-color: #4fc1ff; border: 2px solid #3a95d1; color: #ffffff; text-shadow: 0px 0px 1px #3283b5;',
    'Near Threatened': 'background-color: #67d62f; border: 2px solid #4cb517; color: #ffffff; text-shadow: 0px 0px 1px #47a315;',
    'Vulnerable': 'background-color: #d6ba18; border: 2px solid #cfa715; color: #ffffff; text-shadow: 0px 0px 1px #c28b00;',
    'Endangered': 'background-color: #ff9123; border: 2px solid #c48e21; color: #ffffff; text-shadow: 0px 0px 1px #b38220;',
    'Critically Endangered': 'background-color: #f03022; border: 2px solid #a8482b; color: #ffffff; text-shadow: 0px 0px 1px #7d3a25;',
    'Not Evaluated': 'background-color: #ffffff; border: 2px solid #ebebeb; color: #000000; text-shadow: 0px 0px 2px #ffffff;',
    'Data Deficient': 'background-color: #ffffff; border: 2px solid #ebebeb; color: #000000; text-shadow: 0px 0px 2px #ffffff;',
    'Domesticated': 'background-color: #9C826C; border: 2px solid #85552c; color: #ffffff; text-shadow: 0px 0px 2px #444444;',
    'Extinct': 'background-color: #363636; border: 2px solid #ff4647; color: #ffffff; text-shadow: 0px 0px 2px #000000;',
}

countries = alt.topo_feature(vega_data.world_110m.url, 'countries')

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
                     'Animal name': 'Animal subspecies',
                     'Appearance number': '# Appearances'
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


animal_tab, location_tab = st.tabs(["Search by animal", "Search by location"])

# ------------- USER SELECTION ------------ #

# Filter based on user selections
unique_continents = sorted(raw_data["Continent"].dropna().unique())
unique_countries = sorted(raw_data["Country"].dropna().unique())
unique_classes = sorted(raw_data["Class"].dropna().unique())
unique_families = sorted(raw_data["Family"].dropna().unique())

# Apply continent filter to country selection options
continents_selection = st.sidebar.multiselect("Filter animals by continent", unique_continents, [])
if continents_selection:
    unique_countries = sorted(raw_data.loc[raw_data["Continent"].isin(continents_selection), "Country"].dropna().unique())

countries_selection = st.sidebar.multiselect("Filter animals by country", unique_countries, [])

# Apply class filter to family selection options
class_selection = st.sidebar.multiselect("Filter animals by taxon classes", unique_classes, [])
if class_selection:
    unique_families = sorted(raw_data.loc[raw_data["Class"].isin(class_selection), "Family"].dropna().unique())

families_selection = st.sidebar.multiselect("Filter animals by taxon families", unique_families, [])

# Create filter conditions based on user selections
continents_filter = raw_data["Continent"].isin(continents_selection) | (len(continents_selection) == 0)
countries_filter = (raw_data["Country"].isin(countries_selection)) | (len(countries_selection) == 0)
class_filter = (raw_data["Class"].isin(class_selection)) | (len(class_selection) == 0)
family_filter = (raw_data["Family"].isin(families_selection)) | (len(families_selection) == 0)

st.sidebar.markdown("""---""")

unique_animals = sorted(raw_data["Animal"].dropna().unique())

with animal_tab:
    if (len(continents_selection) == 0) & (len(countries_selection) == 0) & (len(class_selection) == 0) & (len(families_selection) == 0):
        animal_selection = st.selectbox(f"Choose from {len(unique_animals):,} animal species from dropdown or via filters in sidebar", unique_animals, unique_animals.index(sample_animal))
    else:
        filtered_animals = raw_data.loc[continents_filter & countries_filter & class_filter & family_filter, "Animal"].dropna().unique()
        unique_animals = sorted(filtered_animals)
        animal_selection = st.selectbox(f"Choose from {len(unique_animals):,} animal species from dropdown or via filters in sidebar", unique_animals)

        st.markdown("""---""")

    animal_data = raw_data.loc[raw_data["Animal"] == f"{animal_selection}"].copy().sort_values(by=["Air date"])

    if len(animal_data) == 0:
        st.write("<h1 style='color: darkgrey;'>No animals match all filters.</h1><h6 style='color: darkgrey;'>Try expanding your search criteria.</h6>", unsafe_allow_html=True)
    else:
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

        total_images_count = animal_data[["Image 1", "Image 2", "Image 3"]].notnull().sum(axis=1).sum()

        for _, row in animal_data.iterrows():
            if row["Image 1"] is not None:
                show = row["Show"]
                episode = row["Episode"]
                air_date = row["Air date"].strftime("%-d %b %Y")
                air_year = row["Air date"].strftime("%Y")

                if total_images_count <= 6:
                    selected_images = [value for value in [row["Image 1"], row["Image 2"], row["Image 3"]] if
                                       value is not None]
                else:
                    selected_images = [random.choice(
                        [value for value in [row["Image 1"], row["Image 2"], row["Image 3"]] if value is not None])]

                for image in selected_images:
                    path = f"https://ulluri.com/wildlifeonscreen/{show.replace(' ', '%20')}/{episode.replace(' ', '%20')}%20-%20{air_date.replace(' ', '%20')}/{image}.webp"
                    image_paths.append([show, episode, air_year, path])

        if len(image_paths) == 0:
            st.write(
                "<div style='text-align:center;'><h6 style='color: darkgrey;'><i>Images not yet available. Check back soon.</i></h6></div>",
                unsafe_allow_html=True)
        else:
            st.write(
                '<div class="scroll-container">'
                + "".join(
                    f'<div class="image-container"><a href="{image[3]}"><img src="{image[3]}" alt="{image[0] + " - " + image[1] + " (" + image[2] + ")"}" width="250px"></a> <div class="popup-title"><span>{image[0] + " - " + image[1] + " (" + image[2] + ")"}</span></div></div>'
                    for image in image_paths
                )
                + "</div>",
                unsafe_allow_html=True,
            )
        # ------------- MAP ------------ #

        st.markdown(f"<div class='section-banner'><h5>Locations</h5></div>", unsafe_allow_html=True)

        countries_map = alt.Chart(countries).mark_geoshape(
            fill='#353535',
            stroke='#686868',
            strokeWidth=0.3
        ).encode(
            tooltip=alt.value(None),
        ).project('naturalEarth1').interactive()

        points_df = animal_data[(animal_data['Lon'].notna()) & (animal_data['Lat'].notna())].copy()
        if not points_df.empty:
            points_df["Show"] = points_df.apply(lambda x: f'{x["Show"]} ({x["Air date"].strftime("%Y")})', axis=1)

            points = alt.Chart(points_df).mark_circle(opacity=0.5, color='#EDCB0D').encode(
                longitude='Lon:Q',
                latitude='Lat:Q',
                size=alt.value(50),
                tooltip=[alt.Tooltip('Country:N'), alt.Tooltip('Show:N')]
            ).interactive()

            st.altair_chart(countries_map + points, use_container_width=True)
        else:
            st.altair_chart(countries_map, use_container_width=True)

        # ------------- TABLE ------------ #

        st.markdown(f"<div class='section-banner' style='margin-top:-20px;'><h5>Timeline of Appearances</h5></div>", unsafe_allow_html=True)

        table_data = animal_data.copy()

        table_headers = ["Date",
                         "Show",
                         "Episode",
                         "Watch now",
                         "Country",
                         "Continent"]

        if len(table_data["Animal subspecies"].unique()) > 1:
            table_data.rename(columns={'Animal subspecies': 'Name'}, inplace=True)
            table_data["Scientific name"] = table_data["Scientific name"].map(lambda x: f"<i>{x}</i>" if x is not None else "")
            table_data["IUCN status"] = table_data["Subspecies status code"].map(lambda x: f'<span style="{status_css.get(x, "")}" class="ConservationStatusLabel">{x}</span>' if x is not None else "")
            table_headers.extend(["Name", "Scientific name", "IUCN status"])

        table_data["Date"] = table_data["Air date"].apply(lambda x: x.strftime("%-d %b %Y"))

        table_data["Country"] = table_data["Country"].apply(lambda x: x if x is not None else "")

        table_data = table_data.merge(df_episodes[["Show", "Episode", "Streaming_link"]], on=["Show", "Episode"], how="left")

        table_data["Watch now"] = table_data["Streaming_link"].apply(lambda x: f"<a href='{x}'><img src={'https://iplayer-web.files.bbci.co.uk/page-builder/51.0.0/img/icons/favicon.ico' if (not pd.isna(x) and 'bbc' in x) else 'https://assets.nflxext.com/ffe/siteui/common/icons/nficon2016.ico'} width='15px'></a>" if x is not None else "")

        user_sort_selection = st.sidebar.radio(label="Sort Appearances by:",
                                               options=tuple(table_headers))

        if user_sort_selection == "IUCN status":
            table_data.sort_values(by="Subspecies status code", key=lambda x: pd.Categorical(x, categories=status_order, ordered=True), inplace=True)
        elif user_sort_selection == "Date":
            table_data.sort_values(by="Air date", inplace=True)
        else:
            table_data.sort_values(by=user_sort_selection, inplace=True)

        table_data["Show"] = table_data.apply(
            lambda x: f'{x["Show"]} ({x["Air date"].strftime("%Y")})' if x["Air date"] is not None else "", axis=1)


        animal_dot_plot_chart = alt.Chart(
            data=table_data
        ).mark_line(strokeDash=[4, 1], color="#353535").encode(
            x=alt.X("year(Date):T", title="", scale=alt.Scale(domain=[table_data["Air date"].min().year, dt.now().year])),
            y=alt.Y("Animal:N", title="", axis=alt.Axis(labels=False)),
            detail="Animal:N",
        )

        dots = alt.Chart(table_data).mark_circle(size=200, opacity=1).encode(
        # dots = alt.Chart(table_data).mark_point(size=100, opacity=1, shape="triangle-right", strokeWidth=6).encode(
            x=alt.X("year(Date):T", title="", scale=alt.Scale(domain=[table_data["Air date"].min().year, dt.now().year])),
            y=alt.Y("Animal:N", title="", axis=alt.Axis(labels=False)),
            tooltip=[alt.Tooltip('Show:N')],
            color=alt.Color('year(Date):N', scale=alt.Scale(scheme="goldred"), sort="descending", legend=None),
        )

        st.altair_chart(animal_dot_plot_chart + dots, use_container_width=True)

        html_table = table_data[table_headers].drop_duplicates().to_html(escape=False, index=False, classes=['styled-table', 'table-sortable'])

        st.markdown(f"<div class='species_table'>{html_table}</div>", unsafe_allow_html=True)



    # gaussian_jitter = alt.Chart(table_data).mark_line(point=True).encode(
    #     y="Scientific name:N",
    #     x="Date:T",
    #     color=alt.Color('Scientific name:N').legend(None)
    # )


    # st.altair_chart(gaussian_jitter, use_container_width=True)

with location_tab:
    filtered_df = raw_data[continents_filter & countries_filter & class_filter & family_filter].copy()

    if len(filtered_df) == 0:
        st.write(
            "<h1 style='color: darkgrey;'>No animals match all filters.</h1><h6 style='color: darkgrey;'>Try expanding your search criteria.</h6>",
            unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='section-banner'><h5>Species by IUCN Status</h5></div>", unsafe_allow_html=True)

        status_chart_df = filtered_df.groupby("Species status").agg({
            "Binomial name": "nunique"
        }).reset_index()
        status_chart_df.columns = ["IUCN status", "# Species"]

        # status_chart_df["IUCN status"] = status_chart_df["IUCN status code"].apply status_code_labels
        status_chart = alt.Chart(status_chart_df).encode(
            x=alt.X("# Species", axis=alt.Axis(title="# Species", titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed", labelOverlap=True, tickMinStep=1)),
            y=alt.Y("IUCN status", axis=alt.Axis(title="", titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed"), sort=status_order),
            color=alt.Color("IUCN status", scale=alt.Scale(domain=list(status_colours.keys()), range=list(status_colours.values())), legend=None),
        )

        # status_chart = status_chart.mark_bar() + status_chart.mark_text(align='left', dx=2, color='white')
        st.altair_chart(status_chart.mark_bar())

        st.markdown(f"<div class='section-banner'><h5>Species by Country</h5></div>", unsafe_allow_html=True)

        chloropleth_df = filtered_df.groupby(["Country", "ISO3166 ID"]).agg({
            "Binomial name": "nunique"
        }).reset_index()
        chloropleth_df.columns = ["Country", "ISO3166 ID", "NumSpecies"]

        # Sort the DataFrame based on "Unique_BinomialName_Count" in descending order
        sorted_chloropleth_df = chloropleth_df.sort_values(by="NumSpecies", ascending=False)

        # Reset the index and create a new column with row numbers
        sorted_chloropleth_df['RowNumber'] = range(1, len(sorted_chloropleth_df) + 1)
        sorted_chloropleth_df.reset_index(drop=True, inplace=True)

        n = 10
        colour_scheme = "goldgreen"
        # Create two columns for the charts
        col1, col2 = st.columns([0.3, 0.7])

        # Chart 1 - Bar Chart
        with col1:
            country_chart = alt.Chart(sorted_chloropleth_df.head(n)).mark_bar().encode(
                y=alt.Y('Country',
                        axis=alt.Axis(title=f'Top {n} countries', titleFont="Fira Sans Condensed", labelFontSize=12,
                                      labelFont="Fira Sans Condensed", labelOverlap=True), sort="-x"),
                x=alt.X('NumSpecies',
                        axis=alt.Axis(title='# Species', titleFont="Fira Sans Condensed", labelFont="Fira Sans Condensed",
                                      labelOverlap=True, tickMinStep=1)),
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
                from_=alt.LookupData(data=sorted_chloropleth_df, key='ISO3166 ID', fields=['NumSpecies', 'Country'])
            ).transform_calculate(
                NumSpecies='isValid(datum.NumSpecies) ? datum.NumSpecies : -1',
            ).encode(
                color=alt.condition('datum.NumSpecies > 0',
                                    alt.Color('NumSpecies:Q', scale=alt.Scale(scheme=colour_scheme), sort="ascending",
                                              legend=None),
                                    alt.value('#242424')
                                    ),
                tooltip=[
                    alt.Tooltip('Country:N'),
                    alt.Tooltip('NumSpecies:Q', title='# Species')
                ]
            ).project(
                "naturalEarth1"
            ).properties(height=250)

            st.altair_chart(country_map, use_container_width=True)

        table_columns = ["Animal", "Binomial name", "Species status code"]
        st.markdown(f"<div class='section-banner'><h5>List of Species</h5></div>", unsafe_allow_html=True)
        table_df = filtered_df[table_columns].drop_duplicates().copy()
        table_df["IUCN status"] = table_df["Species status code"].map(lambda x: f'<span style="{status_css.get(x, "")}" class="ConservationStatusLabel">{x}</span>' if x is not None else "")
        table_df["Scientific name"] = table_df["Binomial name"]
        table_df = table_df[["Animal", "Scientific name", "IUCN status"]]
        table_df.reset_index(drop=True, inplace=True)
        table_df.index = table_df.index + 1

        # Convert DataFrame to HTML
        html_table = table_df.to_html(escape=False, index=False, classes=['styled-table', 'table-sortable'])

        st.markdown(f"<div class='species_table'>{html_table}</div>", unsafe_allow_html=True)

        # # Convert to first day of the month
        # filtered_df['Air date (month)'] = filtered_df['Air date'].to_numpy().astype('datetime64[M]')
        #
        # gaussian_jitter = alt.Chart(filtered_df).mark_circle(size=12).encode(
        #     y="Species status code:N",
        #     x="Air date:T",
        #     yOffset="jitter:Q",
        #     color=alt.Color('Species status code:N').legend(None)
        # ).transform_calculate(
        #     # Generate Gaussian jitter with a Box-Muller transform
        #     jitter="sqrt(-2*log(random()))*cos(2*PI*random())"
        # )
        #
        # st.altair_chart(gaussian_jitter, use_container_width=True)


        st.markdown(f"<div class='section-banner'><h5>Species appearances over time</h5></div>", unsafe_allow_html=True)

        dot_plot_df = filtered_df.sort_values("Air date", ascending=False).copy()
        dot_plot_df["Show"] = dot_plot_df.apply(lambda x: f'{x["Show"]} ({x["Air date"].strftime("%Y")})' if x["Air date"] is not None else "", axis=1)

        # Group the DataFrame by "Binomial name" and select the first row for each group (highest "Times_Appeared" value)
        last_appearance = dot_plot_df.groupby("Binomial name").first()

        # Group the DataFrame by "Binomial name" and select the first row for each group (lowest "Times_Appeared" value)
        first_appearance = dot_plot_df.groupby("Binomial name").last()

        # Merge the last appearance information back into the original DataFrame
        dot_plot_df = pd.merge(dot_plot_df, last_appearance[["Show", "Episode", "Air date", "# Appearances"]],
                               on="Binomial name",
                               how="left").copy()

        dot_plot_df.rename(columns={
                                  "Show_x": "Show",
                                  "Episode_x": "Episode",
                                  "Air date_x": "Air date",
                                  "Show_y": "Last Appeared In",
                                  "Episode_y": "Last Appeared In Episode",
                                  "Air date_y": "Last Appeared Date",
                                  "# Appearances_y": "# Times Featured"}, inplace=True)

        # Merge the first appearance information back into the original DataFrame
        # dot_plot_df = pd.merge(dot_plot_df, first_appearance[["Show", "Episode", "Air_date"]],
        #                      on="Binomial_name", how="left").copy()
        # dot_plot_df.rename(columns={"Show": "First Appeared In",
        #                           "Episode": "First Appeared In Episode",
        #                           "Air_date": "First Appeared Date"}, inplace=True)

        dot_plot_df.sort_values(by=["Last Appeared Date"], ascending=False, inplace=True)
        max_animals_to_display = 20
        last_appearance_order = dot_plot_df["Animal"].unique()
        most_recent_animals = last_appearance_order[:max_animals_to_display]
        dot_plot_df = dot_plot_df[dot_plot_df["Animal"].isin(most_recent_animals)]

        dot_plot_chart = alt.Chart(
            data=dot_plot_df
        ).mark_line(color='#96b3bdff', point=True, strokeDash=[4, 1]).encode(
            x=alt.X("Air date:T", title=""),
            y=alt.Y("Animal:N", title="", sort=most_recent_animals, axis=alt.Axis(labelLimit=200)),
            detail="Animal:N",
            tooltip=[alt.Tooltip('Animal:N'), alt.Tooltip('Show:N')],
            color=alt.Color('Last Appeared Date:N', scale=alt.Scale(scheme="goldred"), sort="descending", legend=None)
        ).configure_point(
            size=100,
            color='#63c5ff'
        )

        st.altair_chart(dot_plot_chart, use_container_width=True)