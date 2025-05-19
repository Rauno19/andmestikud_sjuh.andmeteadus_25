import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import plotly.express as px
from shapely.ops import unary_union
import matplotlib.ticker as ticker

plt.style.use("seaborn-v0_8-muted")

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
for df in [vakts_df, haigused_df]:
    df.columns = df.columns.str.strip()
    df["Maakond"] = df["Maakond"].str.strip()
    df["Aasta"] = pd.to_numeric(df["Aasta"], errors="coerce")

maakond_gdf["NIMI"] = maakond_gdf["MNIMI"].str.strip()
asustus_gdf["NIMI"] = asustus_gdf["ONIMI"].str.strip()

# --- LISA TALLINN ja NARVA ---
extra_cities = asustus_gdf[asustus_gdf["NIMI"].isin(["Tallinn", "Narva linn"])]
combined_gdf = pd.concat(
    [maakond_gdf[["NIMI", "geometry"]], extra_cities[["NIMI", "geometry"]]],
    ignore_index=True
).drop_duplicates(subset="NIMI")

# --- KASUTAJA VALIKUD ---
aastad = sorted(vakts_df["Aasta"].dropna().unique().astype(int))
haigused_kandidaadid = set(vakts_df.columns) & set(haigused_df.columns) - {"Aasta", "Maakond"}
haigused = sorted(haigused_kandidaadid)

valitud_aasta = st.sidebar.selectbox("🗓 Vali aasta", aastad)
haiguste_arv = st.sidebar.slider("🦠 Mitu haigust soovid võrrelda?", 1, min(5, len(haigused)), 1)
valitud_haigused = st.sidebar.multiselect("🦠 Vali haigused", options=haigused, default=haigused[:haiguste_arv], max_selections=haiguste_arv)
maakonnad = sorted(set(vakts_df["Maakond"]) | set(haigused_df["Maakond"]))
valitud_maakond = st.sidebar.selectbox("📍 Vali maakond", maakonnad)

if not valitud_haigused:
    st.warning("Palun vali vähemalt üks haigus.")
    st.stop()

tabs = st.tabs(valitud_haigused)
for i, valitud_haigus in enumerate(valitud_haigused):
    with tabs[i]:
        vakts = vakts_df.query("Aasta == @valitud_aasta")[["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Vaktsineerimine"})
        haigus = haigused_df.query("Aasta == @valitud_aasta")[["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Haigestumus"})

        geo_df = combined_gdf.merge(vakts, left_on="NIMI", right_on="Maakond", how="left")
        geo_df = geo_df.merge(haigus, on="Maakond", how="left")

        fig, axes = plt.subplots(1, 2, figsize=(20, 10))
        geo_df.plot(column="Vaktsineerimine", cmap="viridis", linewidth=0.3, edgecolor="#f8f8f8", legend=True,
                    ax=axes[0], legend_kwds={"label": "Vaktsineerimise %", "orientation": "horizontal"})
        axes[0].set_title("💉 Vaktsineerimine", fontsize=14)
        axes[0].axis("off")

        geo_df.plot(column="Haigestumus", cmap="OrRd", linewidth=0.3, edgecolor="#f8f8f8", legend=True,
                    ax=axes[1], legend_kwds={"label": "Haigestunute arv", "orientation": "horizontal"})
        axes[1].set_title("🦠 Haigestumus", fontsize=14)
        axes[1].axis("off")
        st.pyplot(fig)

        st.markdown(f"#### 📍 {valitud_maakond} – detailne vaade")

if valitud_maakond != "Eesti kokku":
    col1, col2 = st.columns([1, 2])

    with col1:
        maakond_geom = combined_gdf[combined_gdf["NIMI"] == valitud_maakond]
        if not maakond_geom.empty:
            fig2, ax2 = plt.subplots(figsize=(5, 5))
            maakond_geom.plot(ax=ax2, color="#aad3df", edgecolor="#2c3e50")
            ax2.set_title(valitud_maakond)
            ax2.axis("off")
            st.pyplot(fig2)
        else:
            st.warning("❗ Kehtiv geomeetria puudub.")

    with col2:
        try:
            ha = haigused_df.query("Aasta == @valitud_aasta and Maakond == @valitud_maakond")[valitud_haigus].values[0]
            va = vakts_df.query("Aasta == @valitud_aasta and Maakond == @valitud_maakond")[valitud_haigus].values[0]
            st.metric("Haigestunute arv", f"{int(ha)}")
            st.metric("Vaktsineerimise määr (%)", f"{va}")
        except IndexError:
            st.info("Andmed puuduvad.")

else:
    try:
        ha = haigused_df.query("Aasta == @valitud_aasta and Maakond == @valitud_maakond")[valitud_haigus].values[0]
        va = vakts_df.query("Aasta == @valitud_aasta and Maakond == @valitud_maakond")[valitud_haigus].values[0]
        st.metric("Haigestunute arv", f"{int(ha)}")
        st.metric("Vaktsineerimise määr (%)", f"{va}")
    except IndexError:
        st.info("Andmed puuduvad.")

        st.markdown("#### 📉 Vaktsineerimata vs haigestumus")
        scatter_df = vakts_df[vakts_df["Aasta"] == valitud_aasta][["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Vaktsineerimine"})
        scatter_df = scatter_df.merge(
            haigused_df[haigused_df["Aasta"] == valitud_aasta][["Maakond", valitud_haigus]].rename(columns={valitud_haigus: "Haigestumus"}),
            on="Maakond")
        scatter_df["Vaktsineerimata"] = 100 - scatter_df["Vaktsineerimine"]

        if not scatter_df.empty:
            fig3 = px.scatter(
                scatter_df, x="Vaktsineerimata", y="Haigestumus", text="Maakond",
                color="Haigestumus", color_continuous_scale="Reds",
                title="Seos: vaktsineerimata vs haigestunud"
            )
            fig3.update_traces(textposition="top center")
            st.plotly_chart(fig3, use_container_width=True, key=f"scatter_{valitud_haigus}")

    #   st.markdown("#### 📈 Trend viimase 5 aasta jooksul")
     # eelnevad = [a for a in aastad if a < valitud_aasta][-5:]
      #  vakts_trend = vakts_df.query("Maakond == @valitud_maakond and Aasta in @eelnevad")[["Aasta", valitud_haigus]].rename(columns={valitud_haigus: "Vaktsineerimine"})
       # haigus_trend = haigused_df.query("Maakond == @valitud_maakond and Aasta in @eelnevad")[["Aasta", valitud_haigus]].rename(columns={valitud_haigus: "Haigestumus"})

        #if not vakts_trend.empty and not haigus_trend.empty:
         #   trend_df = vakts_trend.merge(haigus_trend, on="Aasta")
          #  fig4 = px.line(trend_df, x="Aasta", y=["Vaktsineerimine", "Haigestumus"], markers=True, color_discrete_map={
          #      "Vaktsineerimine": "#2980b9", "Haigestumus": "#e74c3c"
          #  })
          #  st.plotly_chart(fig4, use_container_width=True, key=f"trend_{valitud_haigus}")

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
 # --- AJALOOLISED ANDMED ---
    st.markdown(f"#### 📈 {valitud_maakond} – Ajaloolised andmed ({valitud_haigus})")
            
            # Filtreerime vaktsineerimise andmed, et 2024 ja 2025 välja jätta
            # Eeldame, et viimane valideeritud aasta vaktsineerimisandmetega on 2023
            # Kui see on dünaamiline, tuleks seda vastavalt kohandada
    max_vakts_aasta = 2023 # Määratle see vastavalt oma andmetele
    v_ajalugu_filtered = vakts_df.query(
                "Maakond == @valitud_maakond and Aasta <= @max_vakts_aasta"
            )[["Aasta", valitud_haigus]].dropna(subset=[valitud_haigus, "Aasta"])
            
    h_ajalugu = haigused_df.query(
                "Maakond == @valitud_maakond"
            )[["Aasta", valitud_haigus]].dropna(subset=[valitud_haigus, "Aasta"])

    col_hist1, col_hist2 = st.columns(2)
    with col_hist1:
                st.write("**Vaktsineerimise määr (%)**")
                if not v_ajalugu_filtered.empty:
                    fig_hist_v, ax_hist_v = plt.subplots()
                    ax_hist_v.plot(v_ajalugu_filtered["Aasta"], v_ajalugu_filtered[valitud_haigus], marker="o", color="#3498db")
                    ax_hist_v.set_xlabel("Aasta")
                    ax_hist_v.grid(True, linestyle="--", alpha=0.6)
                    ax_hist_v.xaxis.set_major_locator(ticker.MaxNLocator(nbins=5, integer=True)) # Vähendatud nbins
                    st.pyplot(fig_hist_v)
                else:
                    st.info(f"Vaktsineerimise ajaloolised andmed puuduvad.")
            
    with col_hist2:
                st.write("**Haigestumus (juhtumid)**")
                if not h_ajalugu.empty:
                    fig_hist_h, ax_hist_h = plt.subplots()
                    ax_hist_h.plot(h_ajalugu["Aasta"], h_ajalugu[valitud_haigus], marker="o", color="#e74c3c")
                    ax_hist_h.set_xlabel("Aasta")
                    ax_hist_h.grid(True, linestyle="--", alpha=0.6)
                    ax_hist_h.xaxis.set_major_locator(ticker.MaxNLocator(nbins=5, integer=True)) # Vähendatud nbins
                    st.pyplot(fig_hist_h)
                else:
                    st.info(f"Haigestumuse ajaloolised andmed puuduvad.")





# --- KOKKUVÕTE KAHE ERALDI TULPGRAAFIKUNA ---
vakts_data = []
haigus_data = []

for haigus in valitud_haigused:
    try:
        vakts = vakts_df.query("Aasta == @valitud_aasta & Maakond == @valitud_maakond")[haigus].values[0]
        haig = haigused_df.query("Aasta == @valitud_aasta & Maakond == @valitud_maakond")[haigus].values[0]
        vakts_data.append({"Haigus": haigus, "Vaktsineerimine (%)": vakts})
        haigus_data.append({"Haigus": haigus, "Haigestumus (juhtumid)": haig})
    except:
        continue

col_vakts, col_haigus = st.columns(2)

with col_vakts:
    df_vakts = pd.DataFrame(vakts_data)
    fig_vakts = px.bar(df_vakts, x="Haigus", y="Vaktsineerimine (%)", color="Haigus",
                       title=f"{valitud_maakond} – Vaktsineerimise määr ({valitud_aasta})",
                       color_discrete_sequence=px.colors.qualitative.Set2)
    fig_vakts.update_layout(showlegend=False)
    st.plotly_chart(fig_vakts, use_container_width=True)

with col_haigus:
    df_haigus = pd.DataFrame(haigus_data)
    fig_haigus = px.bar(df_haigus, x="Haigus", y="Haigestumus (juhtumid)", color="Haigus",
                        title=f"{valitud_maakond} – Haigestumus ({valitud_aasta})",
                        color_discrete_sequence=px.colors.qualitative.Set1)
    fig_haigus.update_layout(showlegend=False)
    st.plotly_chart(fig_haigus, use_container_width=True)
