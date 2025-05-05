import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# --- LOAD DATA ---

# Vaccination coverage
vakts_df = pd.read_excel("andmestikud/vaktsineerimine.xlsx")
vakts_df = vakts_df.dropna(subset=["Maakond"])
vakts_df["Maakond"] = vakts_df["Maakond"].str.strip()

# Disease incidence
haigused_df = pd.read_excel("andmestikud/Haigused.xlsx")

# GeoJSON for county borders
geojson_path = "andmestikud/maakonnad.geojson"
gdf = gpd.read_file(geojson_path)

# --- SIDEBAR FILTERS ---
aastad = sorted(vakts_df["Aasta"].dropna().unique())
maakonnad = sorted(vakts_df["Maakond"].dropna().unique())

# Include national and city-level data in dropdown
maakonna_valikud = ["Eesti kokku", "Tallinn"] + maakonnad

haigused = vakts_df.columns[2:]  # All disease columns (after "Maakond")

valitud_aasta = st.sidebar.selectbox("Vali aasta", aastad)
valitud_maakond = st.sidebar.selectbox("Vali maakond", maakonna_valikud)
valitud_haigus = st.sidebar.selectbox("Vali haigus", haigused)

# --- MAP PLOT ---
st.subheader(f"💉 Vaktsineerimise määr kaardil – {valitud_haigus} ({valitud_aasta})")

# Filter data for selected year
df_filtered = vakts_df[vakts_df["Aasta"] == valitud_aasta][["Maakond", valitud_haigus]]
df_filtered = df_filtered.rename(columns={valitud_haigus: "Vaktsineerimine"})

# Merge with GeoJSON
merged = gdf.merge(df_filtered, left_on="MNIMI", right_on="Maakond", how="left")

# --- HANDLE "EESTI KOKKU" & "TALLINN" ---
# If "Eesti kokku" or "Tallinn" is selected, show metrics but NOT the map.
if valitud_maakond in ["Eesti kokku", "Tallinn"]:
    st.info(f"📍 Valitud piirkond: **{valitud_maakond}** ei ole kaardil eraldi kujutatud.")

# Otherwise, show the map
elif not merged["Vaktsineerimine"].isnull().all():
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    merged.plot(
        column="Vaktsineerimine",
        cmap="YlGnBu",
        linewidth=0.5,
        edgecolor="white",
        legend=True,
        ax=ax,
        legend_kwds={"label": "Vaktsineerimise %", "orientation": "horizontal"}
    )
    ax.set_title(f"{valitud_haigus} vaktsineerimine maakonniti – {valitud_aasta}")
    ax.axis("off")
    st.pyplot(fig)
else:
    st.warning("❌ Andmeid ei leitud.")

# --- METRICS FOR SELECTED REGION ---
st.subheader(f"📊 Statistika: {valitud_maakond} – {valitud_haigus} ({valitud_aasta})")

# Get vaccination %
vaktsiini_value = vakts_df.query("Aasta == @valitud_aasta and Maakond == @valitud_maakond")[valitud_haigus].values[0]

# Get disease count
haiguse_value = haigused_df.query("Aasta == @valitud_aasta and Maakond == @valitud_maakond")[valitud_haigus].values[0]

# Display metrics
st.metric("Vaktsineerimise määr (%)", f"{vaktsiini_value}")
st.metric("Haigusjuhud", f"{int(haiguse_value)}")
