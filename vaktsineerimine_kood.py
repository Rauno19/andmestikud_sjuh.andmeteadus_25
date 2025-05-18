import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.express as px

# --- SEADISTUS ---
st.set_page_config(layout="wide")
st.title("💉 Vaktsineerimine ja haigestumus maakonniti")

# --- LAE ANDMED ---
vakts_df = pd.read_excel("vaktsineerimine.xlsx")
haigused_df = pd.read_excel("Haigused.xlsx")
maakond_gdf = gpd.read_file("maakond.json")
asustus_gdf = gpd.read_file("asustusyksus.json")
estonia_gdf = gpd.read_file("estonia.json")

# --- PUHASTUS ---
vakts_df.columns = vakts_df.columns.str.strip()
haigused_df.columns = haigused_df.columns.str.strip()
vakts_df["Maakond"] = vakts_df["Maakond"].str.strip()
haigused_df["Maakond"] = haigused_df["Maakond"].str.strip()
maakond_gdf["NIMI"] = maakond_gdf["MNIMI"].str.strip()
asustus_gdf["NIMI"] = asustus_gdf["ONIMI"].str.strip()
vakts_df["Aasta"] = pd.to_numeric(vakts_df["Aasta"], errors="coerce")
haigused_df["Aasta"] = pd.to_numeric(haigused_df["Aasta"], errors="coerce")

# --- LISA TALLINN ja NARVA (ilma "Eesti kokku") ---
extra_cities = asustus_gdf[asustus_gdf["NIMI"].isin(["Tallinn", "Narva linn"])]
combined_gdf = pd.concat(
    [maakond_gdf[["NIMI", "geometry"]], extra_cities[["NIMI", "geometry"]]],
    ignore_index=True
).drop_duplicates(subset="NIMI")

# --- KASUTAJA VALIKUD ---
aastad = sorted(vakts_df["Aasta"].dropna().unique().astype(int))
haigused_kandidaadid = set(vakts_df.columns[~vakts_df.columns.isin(["Aasta", "Maakond"])]).union(
    set(haigused_df.columns[~haigused_df.columns.isin(["Aasta", "Maakond"])]))
haigused = sorted(haigused_kandidaadid)

valitud_aasta = st.sidebar.selectbox("🗓 Vali aasta", aastad)
haiguste_arv = st.sidebar.slider("🦠 Mitu haigust soovid võrrelda?", 1, min(5, len(haigused)), 1)
valitud_haigused = st.sidebar.multiselect("🦠 Vali haigused", options=haigused, default=haigused[:haiguste_arv], max_selections=haiguste_arv)

maakonnad_andmetes = sorted(set(vakts_df["Maakond"]).union(set(haigused_df["Maakond"])))
valitud_maakond = st.sidebar.selectbox("📍 Vali maakond", sorted(set(maakonnad_andmetes)))

if not valitud_haigused:
    st.warning("Palun vali vähemalt üks haigus.")
    st.stop()

# --- KAARDID, STATISTIKA JA GRAAFIKUD ---
for valitud_haigus in valitud_haigused:
    st.markdown(f"### {valitud_haigus} ({valitud_aasta})")

    vaktsineerimine = vakts_df.query("Aasta == @valitud_aasta")[["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Vaktsineerimine"})
    haigestumus = haigused_df.query("Aasta == @valitud_aasta")[["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Haigestumus"})

    geo_df = combined_gdf.copy()
    geo_df = geo_df.merge(vaktsineerimine, left_on="NIMI", right_on="Maakond", how="left")
    geo_df = geo_df.merge(haigestumus, left_on="NIMI", right_on="Maakond", how="left")

    # --- KAARDID ---
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))
    geo_df.plot(column="Vaktsineerimine", cmap="YlGnBu", linewidth=0.5, edgecolor="white", legend=True,
                ax=axes[0], legend_kwds={"label": "Vaktsineerimise %", "orientation": "horizontal"})
    axes[0].set_title("Vaktsineerimise määr")
    axes[0].axis("off")

    geo_df.plot(column="Haigestumus", cmap="Reds", linewidth=0.5, edgecolor="white", legend=True,
                ax=axes[1], legend_kwds={"label": "Haigestunute arv", "orientation": "horizontal"})
    axes[1].set_title("Haigestumus")
    axes[1].axis("off")
    st.pyplot(fig)

    # --- DETAILNE MAAKONNAKAART ---
    st.markdown(f"#### 📍 {valitud_maakond} – detailne vaade")
    col1, col2 = st.columns([1, 2])
    with col1:
        maakond_geom = combined_gdf[combined_gdf["NIMI"] == valitud_maakond]
        if not maakond_geom.empty and maakond_geom.geometry.notnull().all():
            fig2, ax2 = plt.subplots(figsize=(5, 5))
            maakond_geom.plot(ax=ax2, color="lightblue", edgecolor="black")
            ax2.set_title(valitud_maakond)
            ax2.axis("off")
            st.pyplot(fig2)
        else:
            st.warning("❗ Valitud maakonnal puudub kehtiv geomeetria.")

    with col2:
        try:
            ha = haigused_df.query("Aasta == @valitud_aasta and Maakond == @valitud_maakond")[valitud_haigus].values[0]
            va = vakts_df.query("Aasta == @valitud_aasta and Maakond == @valitud_maakond")[valitud_haigus].values[0]
            st.metric("Haigestunute arv", f"{int(ha)}")
            st.metric("Vaktsineerimise määr (%)", f"{va}")
        except IndexError:
            st.write("Andmed puuduvad.")

    # --- VÕRDLUSDIAGRAMM ---
    st.markdown("#### 📉 Vaktsineerimata vs haigestumus")
    scatter_df = vakts_df[vakts_df["Aasta"] == valitud_aasta][["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Vaktsineerimine"})
    scatter_df = scatter_df.merge(
        haigused_df[haigused_df["Aasta"] == valitud_aasta][["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Haigestumus"}),
        on="Maakond")
    scatter_df["Vaktsineerimata"] = 100 - scatter_df["Vaktsineerimine"]

    if not scatter_df.empty:
        fig3 = px.scatter(
            scatter_df, x="Vaktsineerimata", y="Haigestumus", text="Maakond",
            labels={"Vaktsineerimata": "Vaktsineerimata %", "Haigestumus": "Haigestunute arv"},
            title="Seos: vaktsineerimata vs haigestunud"
        )
        fig3.update_traces(textposition="top center")
        st.plotly_chart(fig3, use_container_width=True)

    # --- TRENDIJOON ---
    st.markdown("#### 📈 Trend (eelnevad 5 aastat)")
    eelnevad_aastad = [a for a in aastad if a < valitud_aasta][-5:]
    vakts_ajalugu = vakts_df[(vakts_df["Aasta"].isin(eelnevad_aastad)) & (vakts_df["Maakond"] == valitud_maakond)][["Aasta", valitud_haigus]].rename(columns={valitud_haigus: "Vaktsineerimine"})
    haigus_ajalugu = haigused_df[(haigused_df["Aasta"].isin(eelnevad_aastad)) & (haigused_df["Maakond"] == valitud_maakond)][["Aasta", valitud_haigus]].rename(columns={valitud_haigus: "Haigestumus"})

    if not vakts_ajalugu.empty and not haigus_ajalugu.empty:
        ajalugu_df = vakts_ajalugu.merge(haigus_ajalugu, on="Aasta")
        fig4 = px.line(ajalugu_df, x="Aasta", y=["Vaktsineerimine", "Haigestumus"], markers=True)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("Puuduvad trendi andmed viimase 5 aasta kohta.")

# --- AJAJADA ---
st.subheader(f"📈 {valitud_maakond} – Ajaloolised andmed")
vaktsineerimise_ajalugu = vakts_df[vakts_df["Maakond"] == valitud_maakond][["Aasta", valitud_haigused[0]]].dropna()
haigestumise_ajalugu = haigused_df[haigused_df["Maakond"] == valitud_maakond][["Aasta", valitud_haigused[0]]].dropna()

col1, col2 = st.columns(2)
with col1:
    st.write("**Vaktsineerimise määr (%) aastate lõikes**")
    fig5, ax1 = plt.subplots()
    ax1.plot(vaktsineerimise_ajalugu["Aasta"], vaktsineerimise_ajalugu[valitud_haigused[0]], marker="o", color="blue")
    ax1.set_xlabel("Aasta")
    ax1.set_ylabel("Vaktsineerimine (%)")
    ax1.grid(True)
    st.pyplot(fig5)

with col2:
    st.write("**Haigestumus (juhtumid) aastate lõikes**")
    fig6, ax2 = plt.subplots()
    ax2.plot(haigestumise_ajalugu["Aasta"], haigestumise_ajalugu[valitud_haigused[0]], marker="o", color="red")
    ax2.set_xlabel("Aasta")
    ax2.set_ylabel("Haigestumus")
    ax2.grid(True)
    st.pyplot(fig6)
