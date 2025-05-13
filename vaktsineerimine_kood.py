import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

# --- LAE ANDMED ---
vakts_df = pd.read_excel("andmestikud/vaktsineerimine.xlsx")
haigused_df = pd.read_excel("andmestikud/Haigused.xlsx")
maakond_gdf = gpd.read_file("andmestikud/maakond.json")

# --- VEERUNIMEDE PUHASTUS ---
vakts_df.columns = vakts_df.columns.str.strip().str.replace("\xa0", "", regex=False)
haigused_df.columns = haigused_df.columns.str.strip().str.replace("\xa0", "", regex=False)

# --- ANDMETE ETTEVALMISTUS ---
vakts_df["Maakond"] = vakts_df["Maakond"].str.strip()
haigused_df["Maakond"] = haigused_df["Maakond"].str.strip()

vakts_df["Aasta"] = pd.to_numeric(vakts_df["Aasta"], errors="coerce")
haigused_df["Aasta"] = pd.to_numeric(haigused_df["Aasta"], errors="coerce")

aastad = sorted(vakts_df["Aasta"].dropna().unique().astype(int))

maakond_gdf["NIMI"] = maakond_gdf["MNIMI"].str.strip()
combined_gdf = maakond_gdf.copy()

# --- VALIKUD ---
maakonnad = sorted(
    set(vakts_df["Maakond"].dropna()).union(set(haigused_df["Maakond"].dropna()))
)
maakonna_valikud = [m for m in maakonnad if m != "Eesti kokku"]

# ✅ Ainult veerud, mis on mõlemas olemas
haigused = sorted(
    set(vakts_df.columns).intersection(haigused_df.columns) - {"Aasta", "Maakond"}
)

# --- 🧪 ANDMETE OLEMASOLU TABEL ---
st.subheader("🧪 Andmetabelite täidetus haiguste lõikes")

kontroll_df = pd.DataFrame(columns=["Haigus", "Vaktsineerimine (täidetud)", "Haigestumine (täidetud)"])
for haigus in haigused:
    vakts_count = vakts_df[haigus].dropna().shape[0]
    haigus_count = haigused_df[haigus].dropna().shape[0]
    kontroll_df.loc[len(kontroll_df)] = [haigus, vakts_count, haigus_count]

st.dataframe(kontroll_df.sort_values("Haigus"))

# --- VALIKUD ---
valitud_aasta = st.sidebar.selectbox("Vali aasta", aastad)
valitud_haigus = st.sidebar.selectbox("Vali haigus", haigused)

# --- FILTERDA ANDMED ---
vakts_filtered = vakts_df[
    (vakts_df["Aasta"] == valitud_aasta) & (vakts_df["Maakond"] != "Eesti kokku")
][["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Vaktsineerimine"})

haigus_filtered = haigused_df[
    (haigused_df["Aasta"] == valitud_aasta) & (haigused_df["Maakond"] != "Eesti kokku")
][["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Haigestumus"})

# --- GEOANDMETEGA LIITMINE ---
geo_merged = combined_gdf.merge(
    vakts_filtered, left_on="NIMI", right_on="Maakond", how="left", suffixes=("", "_vakts")
)
geo_merged = geo_merged.merge(
    haigus_filtered, left_on="NIMI", right_on="Maakond", how="left", suffixes=("", "_haigus")
)

# --- KAARDID ---
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
st.subheader("🌐 Kogu Eesti kohta")

try:
    vakts_eesti = vakts_df.query("Aasta == @valitud_aasta and Maakond == 'Eesti kokku'")[valitud_haigus].values[0]
    haigus_eesti = haigused_df.query("Aasta == @valitud_aasta and Maakond == 'Eesti kokku'")[valitud_haigus].values[0]
except IndexError:
    vakts_eesti = haigus_eesti = None

col1, col2 = st.columns(2)
col1.metric("Vaktsineerimise määr (%)", f"{vakts_eesti}" if vakts_eesti is not None else "–")
col2.metric("Haigestunute arv", f"{int(haigus_eesti)}" if haigus_eesti is not None else "–")
