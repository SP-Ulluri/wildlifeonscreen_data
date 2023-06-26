import streamlit as st
from google.oauth2 import service_account
from gsheetsdb import connect
import pandas as pd


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


countries_selection = st.multiselect(
    "Choose countries", unique_countries, ["Kenya"]
)

families_selection = st.multiselect(
    "Choose families", unique_families, ["Felidae"]
)

# Create filter conditions based on user selections
country_filter = (merged_df["Country"].isin(countries_selection)) | (len(countries_selection) == 0)
family_filter = (merged_df["Family"].isin(families_selection)) | (len(families_selection) == 0)

# Apply filters to the DataFrame
filtered_df = merged_df[country_filter & family_filter]


# Display the filtered DataFrame as a table
filtered_df_unique = filtered_df[["Family", "Animal_name", "Binomial_name", "IUCN_status", "Last Appeared In", "Last Appeared Date"]].drop_duplicates().sort_values(["Family", "Binomial_name"])

filtered_df_unique = filtered_df_unique.reset_index(drop=True)
filtered_df_unique.index = filtered_df_unique.index + 1

# st.table(filtered_df_unique)

# Display the DataFrame with interactive sorting enabled
sorted_df = st.dataframe(filtered_df_unique)
