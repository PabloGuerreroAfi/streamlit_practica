# app.py
import os
import pandas as pd
import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
import geopandas as gpd

# =====================================================
# CONFIGURACIÓN STREAMLIT
# =====================================================
st.set_page_config(page_title="Dashboard Delitos y Rentas España", layout="wide")
st.title("Dashboard de Delitos y Renta en España")
st.markdown("Aplicación interactiva para visualizar datos de criminalidad y renta por comunidad, provincia y municipio.")

path = os.getcwd()
path = path + "/data/"

# =====================================================
# LISTA DE EXCELS DE RENTAS
# =====================================================
EXCEL_FILES = [
    f"{path}melilla_datos_rentas.xlsx",
    f"{path}valencia_valència_datos_rentas.xlsx",
    f"{path}almería_datos_rentas.xlsx",

    f"{path}albacete_datos_rentas.xlsx",
    f"{path}alicante_alacant_datos_rentas.xlsx",
    f"{path}araba_álava_datos_rentas.xlsx",
    f"{path}asturias_datos_rentas.xlsx",
    f"{path}avila_datos_rentas.xlsx",
    f"{path}badajoz_datos_rentas.xlsx",

    f"{path}balears illes_datos_rentas.xlsx",
    f"{path}barcelona_datos_rentas.xlsx",
    f"{path}bizkaia_datos_rentas.xlsx",
    f"{path}cáceres_datos_rentas.xlsx",
    f"{path}cádiz_datos_rentas.xlsx",
    f"{path}cantabria_datos_rentas.xlsx",
    f"{path}badajoz_datos_rentas.xlsx",
    f"{path}castellón_castelló_datos_rentas.xlsx",
    f"{path}ceuta_datos_rentas.xlsx",
    f"{path}ciudad real_datos_rentas.xlsx",
    
    f"{path}córdoba_datos_rentas.xlsx",
    f"{path}coruña a_datos_rentas.xlsx",
    f"{path}cuenca_datos_rentas.xlsx",
    f"{path}gipuzkoa_datos_rentas.xlsx",

    f"{path}girona_datos_rentas.xlsx",
    f"{path}granada_datos_rentas.xlsx",
    f"{path}guadalajara_datos_rentas.xlsx",
    f"{path}huelva_datos_rentas.xlsx",
    f"{path}huesca_datos_rentas.xlsx",
    f"{path}jaén_datos_rentas.xlsx",
    f"{path}león_datos_rentas.xlsx",
    f"{path}lleida_datos_rentas.xlsx",
    f"{path}lugo_datos_rentas.xlsx",
    f"{path}madrid_datos_rentas.xlsx",

    f"{path}málaga_datos_rentas.xlsx",
    f"{path}murcia_datos_rentas.xlsx",
    f"{path}navarra_datos_rentas.xlsx",
    f"{path}ourense_datos_rentas.xlsx",
    f"{path}palencia_datos_rentas.xlsx",
    f"{path}palmas las_datos_rentas.xlsx",
    f"{path}pontevedra_datos_rentas.xlsx",
    f"{path}rioja la_datos_rentas.xlsx",
    f"{path}salamanca_datos_rentas.xlsx",
    f"{path}santa cruz de tenerife_datos_rentas.xlsx",
    f"{path}segovia_datos_rentas.xlsx",
    f"{path}sevilla_datos_rentas.xlsx",

    f"{path}tarragona_datos_rentas.xlsx",
    f"{path}teruel_datos_rentas.xlsx",
    f"{path}toledo_datos_rentas.xlsx",
    f"{path}valladolid_datos_rentas.xlsx",
    f"{path}zamora_datos_rentas.xlsx",
    f"{path}zaragoza_datos_rentas.xlsx"
]

# =====================================================
# MAPEOS DE CÓDIGOS A NOMBRE
# =====================================================
codigo_a_comunidad = {
    "01": "Araba/Álava", "02": "Albacete", "03": "Alicante/Alacant", "04": "Almería", "05": "Ávila",
    "06": "Badajoz", "07": "Balears, Illes", "08": "Barcelona", "09": "Burgos", "10": "Cáceres",
    "11": "Cádiz", "12": "Castellón/Castelló", "13": "Ciudad Real", "14": "Córdoba", "15": "Coruña, A",
    "16": "Cuenca", "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Gipuzkoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León", "25": "Lleida", "26": "Rioja, La",
    "27": "Lugo", "28": "Madrid", "29": "Málaga", "30": "Murcia", "31": "Navarra", "32": "Ourense",
    "33": "Asturias", "34": "Palencia", "35": "Palmas, Las", "36": "Pontevedra", "37": "Salamanca",
    "38": "Santa Cruz de Tenerife", "39": "Cantabria", "40": "Segovia", "41": "Sevilla", "42": "Soria",
    "43": "Tarragona", "44": "Teruel", "45": "Toledo", "46": "Valencia/València", "47": "Valladolid",
    "48": "Bizkaia", "49": "Zamora", "50": "Zaragoza", "51": "Ceuta", "52": "Melilla"
}

# =====================================================
# FUNCIÓN DE CARGA DE EXCELS DE RENTAS
# =====================================================
def cargar_excels(lista_excels):
    dfs = []

    for fichero in lista_excels:
        if not os.path.exists(fichero):
            st.warning(f"⚠️ No se encuentra el fichero: {fichero}")
            continue
        df = pd.read_excel(fichero)
        df["fichero_origen"] = fichero
        dfs.append(df)

    if not dfs:
        st.error("❌ No se ha cargado ningún fichero Excel")
        st.stop()

    df_total = pd.concat(dfs, ignore_index=True)
    df_total["codigo_postal"] = df_total["Municipios"].astype(str).str.extract(r"^(\d{5})")
    df_total["comunidad_autonoma"] = df_total["codigo_postal"].str[:2].map(codigo_a_comunidad)

    columnas_renta = [col for col in df_total.columns if "Renta" in col or "Media" in col or "Mediana" in col]
    for col in columnas_renta:
        df_total[col] = pd.to_numeric(df_total[col], errors="coerce")

    return df_total

# =====================================================
# FUNCIÓN DE CARGA DE DATOS DE DELITOS
# =====================================================
@st.cache_data
def cargar_datos_delitos():
    df = pd.read_excel(path + "datos_criminalidad_espana_WIDE.xlsx")
    columnas_num = ['Abril-Junio2023', 'Enero-Marzo2023', 'Julio-Septiembre2023', 'Octubre-Diciembre2023',
                    'Abril-Junio2022', 'Enero-Marzo2022', 'Julio-Septiembre2022', 'Octubre-Diciembre2022',
                    'Total_2023', 'Total_2022', 'Variación_total_2023_2022']
    for col in columnas_num:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce')
    return df

# =====================================================
# CARGA DE DATOS
# =====================================================
df_rentas = cargar_excels(EXCEL_FILES)
df_rentas = df_rentas.dropna(subset=["codigo_postal"])
df_delitos = cargar_datos_delitos()

# =====================================================
# Sidebar: Filtros y opciones DELITOS
# =====================================================
st.sidebar.header("Filtros y Opciones")
opcion = st.sidebar.radio(
    "Selecciona una opción",
    ("Tabla interactiva", "Histograma por tipo de delito", "Gráfico por región", "Mapa de España", "Rentas")
)

comunidad_opciones = df_delitos['Comunidad'].dropna().unique()
provincia_opciones = df_delitos['Provincia'].dropna().unique()
municipio_opciones = df_delitos['Municipio'].dropna().unique()
tipo_delito_opciones = df_delitos['Tipo Delito'].unique()
años = ["2022", "2023", "Variación"]

# =====================================================
# 1. Tabla interactiva DELITOS
# =====================================================
if opcion == "Tabla interactiva":
    st.header("1. Tabla interactiva de delitos")
    st.dataframe(df_delitos)

# =====================================================
# 2. Histograma por tipo de delito
# =====================================================
elif opcion == "Histograma por tipo de delito":
    st.header("2. Histograma por tipo de delito")
    tipo_delito_sel = st.selectbox("Selecciona el tipo de delito:", tipo_delito_opciones)
    df_delito = df_delitos[df_delitos['Tipo Delito'] == tipo_delito_sel]

    hist_data = pd.DataFrame({
        "Año": ["2023", "2022"],
        "Total": [df_delito['Total_2023'].values[0], df_delito['Total_2022'].values[0]]
    })

    fig = px.bar(hist_data, x="Año", y="Total", text="Total",
                 labels={"Total": "Número de delitos"}, color="Año",
                 color_discrete_map={"2023": "crimson", "2022": "royalblue"})
    fig.update_layout(title=f"Comparativa de delitos: {tipo_delito_sel}")
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# 3. Gráfico por región
# =====================================================
elif opcion == "Gráfico por región":
    st.header("3. Delitos por región")
    region_tipo = st.selectbox("Selecciona el nivel de región:", ["Comunidad", "Provincia", "Municipio"])
    
    if region_tipo == "Comunidad":
        region_sel = st.selectbox("Selecciona la comunidad:", comunidad_opciones)
        df_region = df_delitos[df_delitos['Comunidad'] == region_sel]
    elif region_tipo == "Provincia":
        region_sel = st.selectbox("Selecciona la provincia:", provincia_opciones)
        df_region = df_delitos[df_delitos['Provincia'] == region_sel]
    else:
        region_sel = st.selectbox("Selecciona el municipio:", municipio_opciones)
        df_region = df_delitos[df_delitos['Municipio'] == region_sel]

    fig = px.bar(df_region, x="Tipo Delito", y="Total_2023",
                 hover_data=["Total_2022", "Variación_total_2023_2022"],
                 labels={"Total_2023": "Delitos 2023"},
                 title=f"Delitos en {region_sel} ({region_tipo})")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# 4. Mapa interactivo de España
# =====================================================
elif opcion == "Mapa de España":
    st.sidebar.header("Filtros del análisis de criminalidad")

    niveles_agregacion = ["Comunidad", "Provincia"]
    nivel_agregacion = st.sidebar.selectbox("Nivel de agregación", niveles_agregacion)

    tipos_delito = [
        "1. Homicidios dolosos y asesinatos consumados",
        "2. Homicidios dolosos y asesinatos en grado tentativa",
        "3. Delitos graves y menos graves de lesiones y riña tumultuaria",
        "4. Secuestro",
        "5. Delitos contra la libertad sexual",
        "5.1.-Agresión sexual con penetración",
        "5.2.-Resto de delitos contra la libertad sexual",
        "6. Robos con violencia e intimidación",
        "7. Robos con fuerza en domicilios, establecimientos y otras instalaciones",
        "7.1.-Robos con fuerza en domicilios",
        "8. Hurtos",
        "9. Sustracciones de vehículos",
        "10. Tráfico de drogas",
        "11. Resto de criminalidad convencional",
        "12.-Estafas informáticas",
        "13.-Otros ciberdelitos",
        "I. CRIMINALIDAD CONVENCIONAL",
        "II. CIBERCRIMINALIDAD (infracciones penales cometidas en/por medio ciber)",
        "III. TOTAL INFRACCIONES PENALES"
    ]
    tipo_delito = st.sidebar.selectbox("Tipo de delito", tipos_delito)

    trimestres = ["Enero-Marzo", "Abril-Junio", "Julio-Septiembre", "Octubre-Diciembre", "Total"]
    trimestre = st.sidebar.selectbox("Trimestre", trimestres)

    # -------------------------
    # 1. Cargar datos
    # -------------------------

    path_data = fr"{path}datos_criminalidad_espana_WIDE.xlsx"
    df = pd.read_excel(path_data)

    # -------------------------
    # 2. Filtrar por nivel de agregación
    # -------------------------
    normalizacion = {
        "Comunidad": { 'Castilla y León': 'Castilla-Leon', 'Andalucía': 'Andalucia', 'País Vasco': 'Pais Vasco', 'Aragón': 'Aragon', 'Illes Balears': 'Baleares', 'Comunidad Valenciana': 'Valencia', 'Comunidad de Madrid': 'Madrid', 'Ciudad Autónoma de Ceuta': 'Ceuta', 'Ciudad Autónoma de Melilla': 'Melilla', 'Castilla-La Mancha': 'Castilla-La Mancha', 'La Rioja': 'La Rioja', 'Galicia': 'Galicia', 'Extremadura': 'Extremadura', 'Principado de Asturias': 'Asturias', 'Canarias': 'Canarias', 'Cantabria': 'Cantabria', 'Cataluña': 'Cataluña', 'Comunidad Foral de Navarra': 'Navarra', 'Región de Murcia': 'Murcia' },
        "Provincia": { 'Baleares': 'Illes Balears', 'Asturias': 'Asturias', 'A Coruña': 'A Coruña', 'Girona': 'Girona', 'Las Palmas': 'Las Palmas', 'Pontevedra': 'Pontevedra', 'Santa Cruz de Tenerife': 'Santa Cruz De Tenerife', 'Cantabria': 'Cantabria', 'Málaga': 'Málaga', 'Almería': 'Almería', 'Murcia': 'Murcia', 'Albacete': 'Albacete', 'Ávila': 'Ávila', 'Álava': 'Araba/Álava', 'Badajoz': 'Badajoz', 'Alicante':'Alacant/Alicante', 'Ourense': 'Ourense', 'Barcelona': 'Barcelona', 'Burgos': 'Burgos', 'Cáceres': 'Cáceres', 'Cádiz': 'Cádiz', 'Castellón': 'Castelló/Castellón', 'Ciudad Real': 'Ciudad Real', 'Jaén': 'Jaén', 'Córdoba': 'Córdoba', 'Cuenca': 'Cuenca', 'Granada': 'Granada', 'Guadalajara': 'Guadalajara', 'Gipuzkoa': 'Gipuzkoa/Guipúzcoa', 'Huelva': 'Huelva', 'Huesca': 'Huesca', 'León': 'León', 'Lleida': 'Lleida', 'La Rioja': 'La Rioja', 'Soria': 'Soria', 'Navarra': 'Navarra', 'Ceuta': 'Ceuta', 'Lugo': 'Lugo', 'Madrid': 'Madrid', 'Palencia': 'Palencia', 'Salamanca': 'Salamanca', 'Segovia': 'Segovia', 'Sevilla': 'Sevilla', 'Toledo': 'Toledo', 'Tarragona': 'Tarragona', 'Teruel': 'Teruel', 'Valencia': 'València/Valencia', 'Valladolid': 'Valladolid', 'Bizkaia': 'Bizkaia/Vizcaya', 'Zamora': 'Zamora', 'Zaragoza': 'Zaragoza', 'Melilla': 'Melilla' }
    }

    if nivel_agregacion == "Comunidad":
        df_filtrado = df[((df["Provincia"].isna()) | (df["Provincia"] == "")) & ((df["Municipio"].isna()) | (df["Municipio"] == ""))].copy()
        geojson_path = fr"{path}spain-communities.geojson"
        df_filtrado["Region_norm"] = df_filtrado["Comunidad"].replace(normalizacion["Comunidad"])
        merge_key = "Region_norm"
        nombre_columna_geojson = "name"
    else:
        df_filtrado = df[(~df["Provincia"].isna()) & (df["Municipio"].isna())].copy()
        geojson_path = fr"{path}spain-provinces.geojson"
        df_filtrado["Region_norm"] = df_filtrado["Provincia"].replace(normalizacion["Provincia"])
        merge_key = "Region_norm"
        nombre_columna_geojson = "name"

    df_filtrado = df_filtrado[df_filtrado["Tipo Delito"] == tipo_delito].copy()
    if trimestre == "Total":
        col_2023 = "Total_2023"; col_2022 = "Total_2022"; col_var = "Variación_total_2023_2022"
    else:
        col_2023 = f"{trimestre}2023"; col_2022 = f"{trimestre}2022"; col_var = f"{trimestre}_VAR_2023_2022"

    df_filtrado["valor_2023"] = df_filtrado[col_2023]
    df_filtrado["valor_2022"] = df_filtrado[col_2022]
    df_filtrado["variacion"] = df_filtrado[col_var]
    df_filtrado["tipo_delito_tooltip"] = tipo_delito
    df_mapa = df_filtrado[[merge_key, "valor_2023", "valor_2022", "variacion", "tipo_delito_tooltip"]]
    df_mapa["variacion_pct"] = df_mapa["variacion"].astype(str) + "%"

    gdf = gpd.read_file(geojson_path)
    gdf = gdf[[col for col in gdf.columns if not pd.api.types.is_datetime64_any_dtype(gdf[col])]]
    gdf_merged = gdf.merge(df_mapa, left_on=nombre_columna_geojson, right_on=merge_key, how="left")

    m = folium.Map(location=[40, -3.5], zoom_start=6)
    def color_scale(val):
        if pd.isna(val): return "lightgray"
        elif val > 1000: return "#800026"
        elif val > 500: return "#BD0026"
        elif val > 100: return "#E31A1C"
        else: return "#FC4E2A"

    folium.GeoJson(
        gdf_merged,
        style_function=lambda x: {'fillColor': color_scale(x['properties'].get('valor_2023', 0)),
                                'color': 'black', 'weight': 0.5},
        tooltip=folium.features.GeoJsonTooltip(
            fields=[nombre_columna_geojson, "tipo_delito_tooltip", "valor_2023", "valor_2022", "variacion_pct"],
            aliases=[f"{nivel_agregacion}:", "Delito:", f"{trimestre} 2023:", f"{trimestre} 2022:", f"{trimestre}_VAR_2023_2022:"],
            localize=True
        )
    ).add_to(m)

    st.markdown(f"### Mapa de España - Nivel: {nivel_agregacion}")
    st_folium(m, width=1200, height=800)

    st.markdown("### Comparativa por región")
    fig = px.bar(df_filtrado, x="Region_norm", y="valor_2023",
                hover_data=["valor_2022", "variacion"],
                labels={"valor_2023": f"Delitos {trimestre} 2023", "Region_norm": nivel_agregacion},
                color="valor_2023", color_continuous_scale="Reds",
                title=f"Delitos en {nivel_agregacion} - {tipo_delito}")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
# RENTAS
# =====================================================
elif opcion == "Rentas":
    tab1, tab2 = st.tabs([
        "Exploración interactiva renta",
        "Agrupación por CP y Comunidad"
    ])

    # TAB 1 — EXPLORACIÓN INTERACTIVA
    with tab1:
        st.subheader("Explora la renta por municipio")

        col1, col2, col3 = st.columns(3)

        comunidades = sorted(df_rentas["comunidad_autonoma"].dropna().unique())
        comunidad_sel = col1.multiselect(
            "Comunidad autónoma",
            comunidades,
            default=comunidades
        )

        metrica = col2.selectbox(
            "Métrica de renta",
            [
                "Renta neta media por persona 2023",
                "Renta neta media por persona 2022",
                "Renta neta media por hogar 2023",
                "Renta neta media por hogar 2022",
                "Media de la renta por unidad de consumo 2023",
                "Media de la renta por unidad de consumo 2022",
                "Mediana de la renta por unidad de consumo 2023",
                "Mediana de la renta por unidad de consumo 2022",
                "Renta bruta media por persona 2023",
                "Renta bruta media por persona 2022",
                "Renta bruta media por hogar 2023",
                "Renta bruta media por hogar 2022",
            ]
        )

        top_n = col3.slider(
            "Número de municipios",
            min_value=10,
            max_value=100,
            value=30
        )

        df_filtro = df_rentas[df_rentas["comunidad_autonoma"].isin(comunidad_sel)].dropna(subset=[metrica])

        m1, m2, m3 = st.columns(3)
        m1.metric("Media", f"{df_filtro[metrica].mean():,.0f} €")
        m2.metric("Mediana", f"{df_filtro[metrica].median():,.0f} €")
        m3.metric("Municipios", len(df_filtro))

        ranking = df_filtro.sort_values(metrica, ascending=False).head(top_n)

        fig_ranking = px.bar(
            ranking,
            x="Municipios",
            y=metrica,
            color="comunidad_autonoma",
            title=f"Top {top_n} municipios por {metrica}",
        )

        st.plotly_chart(fig_ranking, use_container_width=True)
        st.dataframe(ranking, use_container_width=True)

    # TAB 2 — AGRUPACIÓN POR CP / COMUNIDAD
    with tab2:
        st.subheader("Perfil medio de renta por comunidad autónoma")

        agrupado = (
            df_rentas.groupby("comunidad_autonoma")
            .agg(
                renta_neta_persona_2023=("Renta neta media por persona 2023", "mean"),
                renta_neta_hogar_2023=("Renta neta media por hogar 2023", "mean"),
                renta_uc_media_2023=("Media de la renta por unidad de consumo 2023", "mean"),
                renta_uc_mediana_2023=("Mediana de la renta por unidad de consumo 2023", "mean"),
                municipios=("Municipios", "count")
            )
            .reset_index()
            .sort_values("renta_neta_persona_2023", ascending=False)
        )

        fig_ca = px.bar(
            agrupado,
            x="comunidad_autonoma",
            y="renta_neta_persona_2023",
            title="Renta neta media por persona (2023)"
        )

        fig_evol = px.scatter(
            df_rentas,
            x="Renta neta media por persona 2022",
            y="Renta neta media por persona 2023",
            color="comunidad_autonoma",
            hover_name="Municipios",
            title="Evolución renta neta por municipio (2022 → 2023)"
        )

        st.plotly_chart(fig_ca, use_container_width=True)
        st.plotly_chart(fig_evol, use_container_width=True)
        st.dataframe(agrupado, use_container_width=True)

# =====================================================
# Footer
# =====================================================
st.markdown("---")
st.markdown("Aplicación creada por **Pablo Guerrero Álvarez**")