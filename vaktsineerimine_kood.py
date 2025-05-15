import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.express as px

st.set_page_config(layout="wide")
st.title("💉 Vaktsineerimine ja haigestumus maakonniti")

# --- LAE ANDMED ---
vakts_df = pd.read_excel("vaktsineerimine.xlsx")
haigused_df = pd.read_excel("Haigused.xlsx")
maakond_gdf = gpd.read_file("maakond.json")
asustus_gdf = gpd.read_file("asustusyksus.json")

# --- PUHASTUS ---
vakts_df.columns = vakts_df.columns.str.strip()
haigused_df.columns = haigused_df.columns.str.strip()
vakts_df["Maakond"] = vakts_df["Maakond"].str.strip()
haigused_df["Maakond"] = haigused_df["Maakond"].str.strip()
maakond_gdf["NIMI"] = maakond_gdf["MNIMI"].str.strip()
asustus_gdf["NIMI"] = asustus_gdf["ONIMI"].str.strip()
vakts_df["Aasta"] = pd.to_numeric(vakts_df["Aasta"], errors="coerce")
haigused_df["Aasta"] = pd.to_numeric(haigused_df["Aasta"], errors="coerce")

# --- LISA TALLINN JA NARVA ---
extra_cities = asustus_gdf[asustus_gdf["NIMI"].isin(["Tallinn", "Narva linn"])]
combined_gdf = pd.concat([
    maakond_gdf[["NIMI", "geometry"]],
    extra_cities[["NIMI", "geometry"]]
], ignore_index=True)

# --- KASUTAJA VALIKUD ---
aastad = sorted(vakts_df["Aasta"].dropna().unique().astype(int))
kõik_maakonnad = sorted(set(vakts_df["Maakond"].dropna()))
if "Eesti kokku" not in kõik_maakonnad:
    kõik_maakonnad.insert(0, "Eesti kokku")

# Haigused ainult vakts_df alusel (või tee vajadusel ühildamisega)
haigused = sorted(set(vakts_df.columns) - {"Aasta", "Maakond"})

st.sidebar.header("🎛️ Valikud")
valitud_aasta = st.sidebar.selectbox("🗓 Vali aasta", aastad)
valitud_haigused = st.sidebar.multiselect("🦠 Vali haigused (1-5)", haigused, default=haigused[:1], max_selections=5)
valitud_maakond = st.sidebar.selectbox("📍 Vali maakond", kõik_maakonnad)

if not valitud_haigused:
    st.warning("Palun vali vähemalt üks haigus.")
    st.stop()

# --- VALMISTA ANDMED ---
vakts_data = vakts_df.query("Aasta == @valitud_aasta").copy()
vakts_data["Vaktsineerimine"] = vakts_data[valitud_haigused].mean(axis=1)
vakts_data = vakts_data[["Maakond", "Vaktsineerimine"]]

haigus_data = haigused_df.query("Aasta == @valitud_aasta").copy()
haigus_data["Haigestumus"] = haigus_data[valitud_haigused].mean(axis=1)
haigus_data = haigus_data[["Maakond", "Haigestumus"]]

geo_df = combined_gdf.copy()
geo_df = geo_df.merge(vakts_data, left_on="NIMI", right_on="Maakond", how="left")
geo_df = geo_df.merge(haigus_data, left_on="NIMI", right_on="Maakond", how="left")

# --- KAARDID JA STATISTIKA ---
st.subheader(f"🌍 {', '.join(valitud_haigused)} ({valitud_aasta})")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Vaktsineerimise määr")
    fig1, ax1 = plt.subplots(figsize=(10, 8))
    geo_df.plot(column="Vaktsineerimine", cmap="YlGnBu", linewidth=0.5,
                edgecolor="white", legend=True, ax=ax1,
                legend_kwds={"label": "Vaktsineerimise %", "orientation": "horizontal"})
    ax1.axis("off")
    st.pyplot(fig1)

    # Vaktsineerimise statistika
    st.markdown("<small><b>Keskmine vaktsineerimine:</b></small>", unsafe_allow_html=True)
    try:
        vakts_väärtus = vakts_data.query("Maakond == @valitud_maakond")["Vaktsineerimine"].values[0]
        st.metric("", f"{vakts_väärtus:.1f} %")
    except:
        st.warning("❌ Andmed puuduvad.")

with col2:
    st.markdown("#### Haigestumus")
    fig2, ax2 = plt.subplots(figsize=(10, 8))
    geo_df.plot(column="Haigestumus", cmap="Reds", linewidth=0.5,
                edgecolor="white", legend=True, ax=ax2,
                legend_kwds={"label": "Haigestunute arv", "orientation": "horizontal"})
    ax2.axis("off")
    st.pyplot(fig2)

    # Haigestumise statistika
    st.markdown("<small><b>Keskmine haigestumus:</b></small>", unsafe_allow_html=True)
    try:
        haigus_väärtus = haigus_data.query("Maakond == @valitud_maakond")["Haigestumus"].values[0]
        st.metric("", f"{haigus_väärtus:.1f}")
    except:
        st.warning("❌ Andmed puuduvad.")

# --- TREND ---
st.subheader("📈 Vaktsineerimise ja haigestumise trend (eelnevad 5 aastat)")
eelnevad_aastad = [a for a in aastad if a < valitud_aasta][-5:]

vakts_trend = vakts_df[vakts_df["Aasta"].isin(eelnevad_aastad) & (vakts_df["Maakond"] == valitud_maakond)].copy()
vakts_trend["Vaktsineerimine"] = vakts_trend[valitud_haigused].mean(axis=1)
vakts_trend = vakts_trend[["Aasta", "Vaktsineerimine"]].sort_values("Aasta")

haigus_trend = haigused_df[haigused_df["Aasta"].isin(eelnevad_aastad) & (haigused_df["Maakond"] == valitud_maakond)].copy()
haigus_trend["Haigestumus"] = haigus_trend[valitud_haigused].mean(axis=1)
haigus_trend = haigus_trend[["Aasta", "Haigestumus"]].sort_values("Aasta")

if not vakts_trend.empty and not haigus_trend.empty:
    merged = pd.merge(vakts_trend, haigus_trend, on="Aasta")
    fig3 = px.line(merged, x="Aasta", y=["Vaktsineerimine", "Haigestumus"],
                   markers=True, title="Vaktsineerimise ja haigestumise trend", labels={
                       "value": "Väärtus", "variable": "Mõõdik"
                   })
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.warning("⚠️ Trendide joonistamiseks puuduvad andmed.")

# --- VÕRDLUS ---
st.subheader("📊 Haigestunute arv vs vaktsineerimata osakaal")
try:
    vakts_row = vakts_data[vakts_data["Maakond"] == valitud_maakond]
    haigus_row = haigus_data[haigus_data["Maakond"] == valitud_maakond]

    if not vakts_row.empty and not haigus_row.empty:
        vaktsineerimata = 100 - vakts_row["Vaktsineerimine"].values[0]
        haigestunud = haigus_row["Haigestumus"].values[0]

        df_vordlus = pd.DataFrame({
            "Näitaja": ["Vaktsineerimata osakaal (%)", "Haigestunute arv"],
            "Väärtus": [vaktsineerimata, haigestunud]
        })

        fig4 = px.bar(df_vordlus, x="Näitaja", y="Väärtus", color="Näitaja", text="Väärtus")
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.warning("⚠️ Valitud piirkonna kohta puuduvad andmed.")
except Exception as e:
    st.error(f"❌ Viga võrdlusgraafiku loomisel: {e}")
