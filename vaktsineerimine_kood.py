import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# --- LAE ANDMED ---
vakts_df = pd.read_excel("vaktsineerimine.xlsx")
haigused_df = pd.read_excel("Haigused.xlsx")
maakond_gdf = gpd.read_file("EHAK/geojson/maakond.json")
asustus_gdf = gpd.read_file("EHAK/geojson/asustusyksus.json")

# --- ANDMETE ETTEVALMISTUS ---
vakts_df.columns = vakts_df.columns.str.strip()
haigused_df.columns = haigused_df.columns.str.strip()

vakts_df["Maakond"] = vakts_df["Maakond"].str.strip()
haigused_df["Maakond"] = haigused_df["Maakond"].str.strip()

# Lisa Tallinn ja Narva kaardile
cities_gdf = asustus_gdf[asustus_gdf["ONIMI"].isin(["Tallinn", "Narva"])]
combined_gdf = pd.concat([maakond_gdf, cities_gdf], ignore_index=True)
combined_gdf["NIMI"] = combined_gdf["MNIMI"].fillna(combined_gdf["ONIMI"]).str.strip()

# --- VALIKUD ---
aastad = sorted(vakts_df["Aasta"].dropna().unique())
maakonnad = sorted(set(vakts_df["Maakond"]).union(haigused_df["Maakond"]))
maakonna_valikud = [m for m in maakonnad if m != "Eesti kokku"]
haigused = [col for col in vakts_df.columns if col not in ["Aasta", "Maakond"]]

valitud_aasta = st.sidebar.selectbox("Vali aasta", aastad)
valitud_haigus = st.sidebar.selectbox("Vali haigus", haigused)

# --- FILTERDA ANDMED ---
vakts_filtered = vakts_df[
    (vakts_df["Aasta"] == valitud_aasta) &
    (vakts_df["Maakond"] != "Eesti kokku")
][["Maakond", valitud_haigus]]
vakts_filtered = vakts_filtered.rename(columns={valitud_haigus: "Vaktsineerimine"})

haigus_filtered = haigused_df[
    (haigused_df["Aasta"] == valitud_aasta) &
    (haigused_df["Maakond"] != "Eesti kokku")
][["Maakond", valitud_haigus]]
haigus_filtered = haigus_filtered.rename(columns={valitud_haigus: "Haigestumus"})

# --- GEOANDMETEGA LIITMINE ---
geo_merged = combined_gdf.merge(
    vakts_filtered, left_on="NIMI", right_on="Maakond", how="left", suffixes=("", "_vakts")
)
geo_merged = geo_merged.merge(
    haigus_filtered, left_on="NIMI", right_on="Maakond", how="left", suffixes=("", "_haigus")
)

# --- DEBUG KUVA VAJADUSEL ---
# st.write("Vaktsineerimise andmed", vakts_filtered)
# st.write("Haigestumise andmed", haigus_filtered)
# st.write("Liidetud geoandmed", geo_merged[["NIMI", "Vaktsineerimine", "Haigestumus"]])

# --- KUVA KAARDID ---
st.subheader(f"{valitud_haigus} ({valitud_aasta}) vaktsineerimine ja haigestumus maakonniti")

fig, axes = plt.subplots(1, 2, figsize=(20, 10))

# Vaktsineerimise kaart
geo_merged.plot(
    column="Vaktsineerimine",
    cmap="YlGnBu",
    linewidth=0.5,
    edgecolor="white",
    legend=True,
    ax=axes[0],
    legend_kwds={"label": "Vaktsineerimise %", "orientation": "horizontal"}
)
axes[0].set_title("Vaktsineerimise määr")
axes[0].axis("off")

# Haigestumuse kaart
geo_merged.plot(
    column="Haigestumus",
    cmap="Reds",
    linewidth=0.5,
    edgecolor="white",
    legend=True,
    ax=axes[1],
    legend_kwds={"label": "Haigestunute arv", "orientation": "horizontal"}
)
axes[1].set_title("Haigestumus")
axes[1].axis("off")

st.pyplot(fig)

# --- KUVA EESTI KOKKU ---
st.subheader(f"🌐 Kogu Eesti kohta")

vakts_eesti = vakts_df.query("Aasta == @valitud_aasta and Maakond == 'Eesti kokku'")[valitud_haigus].values[0]
haigus_eesti = haigused_df.query("Aasta == @valitud_aasta and Maakond == 'Eesti kokku'")[valitud_haigus].values[0]

col1, col2 = st.columns(2)
col1.metric("Vaktsineerimise määr (%)", f"{vakts_eesti}")
col2.metric("Haigestunute arv", f"{int(haigus_eesti)}")