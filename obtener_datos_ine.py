import pandas as pd
import requests
import selenium
import os
from io import StringIO

import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

#Se ha decidido que se van a obtener los datos para 2022 y 2023. Esto es principalmente porque los datos de renta limitan la fecha más reciente.

def reestructurar_excel_datos_criminalidad(df, trimestre):
    def esta_en_mayusculas(s):
        return isinstance(s, str) and any(c.isalpha() for c in s) and s.isupper()

    trimestre = trimestre.replace("_", "-")
    # Renombrar columna
    df = df.rename(columns={"Unnamed: 0": "Texto"})

    tratamiento_especial = {
        "CIUDAD AUTÓNOMA DE CEUTA",
        "CIUDAD AUTÓNOMA DE MELILLA",
        "EN EL EXTRANJERO",
        "NACIONAL"
    }

    datos = {
        "Comunidad": [],
        "Provincia": [],
        "Municipio": [],
        "Tipo Delito": [],
        "Trimestre": [],
        "Dato 2023": [],
        "Dato 2022": [],
        "Variación 2023/2022": []
    }

    comunidad = None
    provincia = None
    municipio = None

    for _, row in df.iterrows():
        texto = row["Texto"]

        # Comunidades y especiales
        if esta_en_mayusculas(texto) and texto not in {"I. CRIMINALIDAD CONVENCIONAL",
                                                      "II. CIBERCRIMINALIDAD (infracciones penales cometidas en/por medio ciber)",
                                                      "III. TOTAL INFRACCIONES PENALES"}:
            comunidad = texto
            provincia = None
            municipio = None
            continue

        # Provincias
        if isinstance(texto, str) and texto.startswith("Provincia de"):
            provincia = texto
            municipio = None
            continue

        # Municipios
        if isinstance(texto, str) and (
            texto.startswith("-Municipio de") or texto.startswith("Municipio de") or
            texto.startswith("Municipo de") or texto.startswith("Isla de") or
            texto.startswith("-Municipo de") or texto.startswith("CIUDAD AUTÓNOMA")
        ):
            municipio = texto.lstrip("-")
            continue

        # Filas con datos (incluyendo categorías I, II, III)
        if pd.notna(row[f"{trimestre} 2022"]):
            datos["Comunidad"].append(comunidad)
            datos["Provincia"].append(provincia)
            datos["Municipio"].append(municipio)
            datos["Tipo Delito"].append(texto)
            datos["Trimestre"].append(trimestre)
            datos["Dato 2023"].append(pd.to_numeric(row[f"{trimestre} 2023"], errors='coerce'))
            datos["Dato 2022"].append(pd.to_numeric(row[f"{trimestre} 2022"], errors='coerce'))
            datos["Variación 2023/2022"].append(pd.to_numeric(row["Variación % 2023/2022"], errors='coerce'))

    df_final = pd.DataFrame(datos)

    # None en lugar de "Columna Vacía"
    df_final["Provincia"] = df_final["Provincia"].where(df_final["Provincia"].notna(), None)
    df_final["Municipio"] = df_final["Municipio"].where(df_final["Municipio"].notna(), None)

    # Ordenar
    df_final = df_final.sort_values(
        by=["Comunidad", "Provincia", "Municipio", "Tipo Delito"],
        key=lambda col: col.fillna('')
    ).reset_index(drop=True)

    return df_final


def obtener_datos_ine_rentas(path):

    url_ine_datos_demograficos = 'https://www.ine.es/dynt3/inebase/index.htm?padre=12385'

    
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    browser.maximize_window()
    browser.get(url = url_ine_datos_demograficos)

    
    desplegar_resultados_por_municipios = (WebDriverWait(browser, 10)
                      .until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a#c_12384'))))
    desplegar_resultados_por_municipios.click()

    desplegar_resultados_por_municipios_continuacion = (WebDriverWait(browser, 10)
                      .until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'a#c_7132'))))
    desplegar_resultados_por_municipios_continuacion.click()

    # Todas las provincias
    # 1. Hay que hacer click en cada desplegable para que carguen las opciones.
    # 2. Dentro de cada provincia, se clica en los indicadores de renta media y mediana. Esto te lleva a otra página

    WebDriverWait(browser, 10).until(
    EC.presence_of_element_located(
        (By.CSS_SELECTOR, "a#c_7132 + ul.subSecc")
    )
    )

    ###############
    # EXPLICACIÓN #
    ###############

    # En este momento es cuando obtenemos las provincias almacenadas en una lista <ul>.
    # Cada elemento a su vez es una lista <li> con un elemento inicial <a> que es necesario clicar.
    # Una vez clicado, se genera otro elemento <ul> que es donde estan todas las pestañas donde se almacenan los datos de renta, ingresos por unidad de consumo, indicadores demográficos. 
    # Aquí es donde vamos a clicar (indicadores de renta media y mediana) y nos va a redirigir a una página diferente donde podremos obtenener los datos.

    #Para cada provincia, vamos a obtener los datos de 2022 y 2023 de todos los indicadores, para cada municipio.


    provincias = browser.find_elements(
        By.CSS_SELECTOR, "a#c_7132 + ul.subSecc li.full > a"
    )

    # Almacenaremos en un diccionario {nombre_provincia: url} las urls de las páginas donde se obtendran los datos de renta media y mediana por provincia
    diccionario_de_urls = {}
    for i in range(len(provincias)):
        try:
            provincias = browser.find_elements(
                By.CSS_SELECTOR, "a#c_7132 + ul.subSecc li.full > a"
            )
            provincia = provincias[i]

            browser.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", provincia
            )

            nombre = provincia.text.strip()
            expanded = provincia.get_attribute("aria-expanded")

            print(f"{nombre}")

            if expanded == "false":
                provincia.click()

                WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, f"a#{provincia.get_attribute('id')} + ul.subSecc")))

                #Ahora es cuando clicamos en "Indicadores de renta media y mediana"
                # <ul> -> <li>,<li>...
                # Unicamente quiero el primer elemento <li>
                desplegar_resultados_por_municipios_continuacion = (WebDriverWait(browser, 10)
                      .until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a#{provincia.get_attribute('id')} + ul.subSecc > li:first-child > a"))))
                
                #Guardar las urls como he explicado antes
                diccionario_de_urls.update({nombre : desplegar_resultados_por_municipios_continuacion.get_attribute("href")})

        except Exception:
            continue

    #Check para comprobar que el número de provincias obtenidas coincide con el tamaño del diccionario. Evitar algún posible error de la pagina

    if len(diccionario_de_urls) != len(provincias): 
        raise Exception("Falta alguna provincia")

    #Recorremos el diccionario para obtener los datos de las provincias. 2022 y 2023

    for nombre_provincia, url_datos_provincia in diccionario_de_urls.items():
        print(nombre_provincia, url_datos_provincia)
        nombre_provincia = nombre_provincia.replace("/", "_").replace(",", "")
        
        browser.get(url = url_datos_provincia)

        tabla_valores = browser.find_element(
                By.CSS_SELECTOR, "ul.secciones > li > ul#variables"
            )
        browser.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", tabla_valores
            )
        
        # Ahora seleccionamos las opciones en cada una de las tablas.
        # De indicadores seleccionamos todos y de fechas unicamente 2023 y 2022
        # De unidades territoriales seleccionamos unicamente los municipios.
        # Para una futura implementacion (ya lo hice en mi tfg), se podría seleccionar hasta secciones censales.

        tabla_periodo = browser.find_element(By.CSS_SELECTOR, "ul#variables select#periodo")
        select_tabla_periodo = Select(tabla_periodo)
        select_tabla_periodo.select_by_value("28~2023")
        select_tabla_periodo.select_by_value("28~2022")

        tabla_indicadores_renta_media_y_mediana = browser.find_element(By.CSS_SELECTOR, "ul#variables select.cajaVariables")
        select_tabla_indicadores_renta_media_y_mediana = Select(tabla_indicadores_renta_media_y_mediana)
        select_tabla_indicadores_renta_media_y_mediana.select_by_visible_text("Renta neta media por persona")
        select_tabla_indicadores_renta_media_y_mediana.select_by_visible_text("Renta neta media por hogar")
        select_tabla_indicadores_renta_media_y_mediana.select_by_visible_text("Media de la renta por unidad de consumo")
        select_tabla_indicadores_renta_media_y_mediana.select_by_visible_text("Mediana de la renta por unidad de consumo")
        select_tabla_indicadores_renta_media_y_mediana.select_by_visible_text("Renta bruta media por persona")
        select_tabla_indicadores_renta_media_y_mediana.select_by_visible_text("Renta bruta media por hogar")

        input_distritos = browser.find_element(By.CSS_SELECTOR, "ul#variables input#selCri_1")
        input_distritos.click()
        input_secciones = browser.find_element(By.CSS_SELECTOR, "ul#variables input#selCri_2")
        input_secciones.click()
        
        # Para aceptar el boton de cookies.
        try:
            boton_cookies = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a#aceptarCookie"))
            )
            boton_cookies.click()

            # esperar a que desaparezca el banner
            WebDriverWait(browser, 10).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, "a#aceptarCookie"))
            )
        except:
            pass

        #Una vez seleccionadas las opciones, le damos al boton de "consultar selección"
        boton_consultar_seleccion = browser.find_element(By.CSS_SELECTOR, "input#botonConsulSele")
        boton_consultar_seleccion.click()

        url_con_datos_provincia = browser.current_url
        print(f"La url donde esta la tabla con los resultados es: {url_con_datos_provincia}")

        #Esperamos a que la tabla con los datos esté cargada
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "tablaDatos")))

        # Para leer la tabla utilizare beautifulsoup. La tabla esta localizada en el elemento <table id=tablaDatos>.
        # Dentro de esta tabla hay un thead con los nombres de las columnas y un tbody con los datos. Cada fila es un municipio
        html_tabla = browser.find_element(By.ID, "tablaDatos").get_attribute("outerHTML")
        web_tabla_con_datos_provincia = BeautifulSoup(html_tabla, "html.parser")
        table = web_tabla_con_datos_provincia.select("table#tablaDatos")[0]
        df_tabla_final = pd.read_html(str(table), header=0, decimal=",", thousands=".")[0]

        df_tabla_final.columns = ["Municipios", 
                                  "Renta neta media por persona 2023", "Renta neta media por persona 2022",
                                  "Renta neta media por hogar 2023", "Renta neta media por hogar 2022",
                                  "Media de la renta por unidad de consumo 2023", "Media de la renta por unidad de consumo 2022",
                                  "Mediana de la renta por unidad de consumo 2023", "Mediana de la renta por unidad de consumo 2022",
                                  "Renta bruta media por persona 2023", "Renta bruta media por persona 2022",
                                  "Renta bruta media por hogar 2023", "Renta bruta media por hogar 2022"]
        df_tabla_final = df_tabla_final[1:]
        df_tabla_final.to_excel(path + fr"\{nombre_provincia.lower()}_datos_rentas.xlsx")

    browser.close()
    print("Se ha completado la obtención de los datos de rentas del INE")


def obtener_datos_ine_criminalidad(path):

    url_minterior_datos_criminalidad = 'https://estadisticasdecriminalidad.ses.mir.es/publico/portalestadistico/'

    
    browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    browser.maximize_window()
    browser.get(url = url_minterior_datos_criminalidad)

    # Para aceptar el boton de cookies.
    try:
        boton_cookies = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button#AceptoCookies"))
        )
        time.sleep(0.7)
        boton_cookies.click()
        time.sleep(0.7)

        # esperar a que desaparezca el banner
        WebDriverWait(browser, 10).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "button#AceptoCookies"))
        )
    except:
        pass

    #Para que parezca un poco natural, añado un sleep entre acciones
    boton_acceder_balance_criminalidad = (WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'main section div.card-footer'))))
    boton_acceder_balance_criminalidad.click()
    time.sleep(0.7)

    # Hacemos scroll hasta el año 2025. Lo cerramos para que aparezcan los demás sin necesidad de hacer scroll "x" pixeles
    # Abrimos el año 2023.
    # Puesto que en estos balances trimestrales, te dan la posibilidad de obtener los valores del mismo trimestre del año anterior,
    # no es necesario consultar 2022 utilizando web scraping. Basta con obtener los datos de los 4 trimestres de 2023 y realizar un tratamiento de los datos
    boton_ultimo_anio = browser.find_element(By.CSS_SELECTOR, "button.accordion-button")
    browser.execute_script("arguments[0].scrollIntoView({block:'center'});", boton_ultimo_anio)
    time.sleep(0.7)
    boton_ultimo_anio.click()
    time.sleep(0.7)

    boton_2023 = (WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.XPATH,"//button[.//span[normalize-space()='Año 2023']]"))))
    browser.execute_script("arguments[0].scrollIntoView({block:'center'});", boton_2023)
    boton_2023.click()
    time.sleep(0.7)

    # Ahora obtengo todos los botones trimestrales
    # Para no obtener el acordeon (card body que contiene los botones para 2023)
    # puedo filtrar para que encuentre el div cuyo padre tenga el id = id_anio_2023
    accordion_id = boton_2023.get_attribute("aria-controls")

    accordion_2023 = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, accordion_id))
    )
    botones_trimestres = accordion_2023.find_elements(By.CSS_SELECTOR, "ul.list-group li a")

    #Para obtener el dato, recorremos los 4 botones de los trimestres.
    dict_trimestres = {1: "Enero_marzo", 2: "Enero_junio", 3: "enero_septiembre", 4: "enero_diciembre"}

    hrefs_trimestres = [boton.get_attribute("href") for boton in botones_trimestres]

    for i, href in enumerate(hrefs_trimestres, start=1):
        print(f"Trimestre {i}: {href}")
        browser.get(url = href)

        # Este es el desplegable con las estadisticas. Por defecto se abre nada mas visitar la página.
        # En caso de que en un futuro modifiquen la página, hago un check para comprobar si esta desplegado o no. Si no esta desplegado, hago click
        boton_estadisticas_x_trimestre = (WebDriverWait(browser, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR,"button.accordion-button"))))
        if boton_estadisticas_x_trimestre.get_attribute("aria-expanded") != "true":
            time.sleep(0.7)
            boton_estadisticas_x_trimestre.click()
            time.sleep(0.7)


        # El boton con el enlace a las estadisticas esta dentro de un iframe. un iframe es un html dentro de otro html
        # Es necesario cambiar el browser al html del iframe
        # Despues ya podemos seleccionar el ultimo elemento dentro de la lista <li> que esta dentro de <ul.secciones>
        iframe = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "iframeINE"))
        )

        # Cambiamos el contexto de Selenium al iframe
        browser.switch_to.frame(iframe)

        # Ahora sí podemos buscar el último li dentro de ul.secciones
        ul_secciones = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.secciones"))
        )
        li_secciones = ul_secciones.find_elements(By.TAG_NAME, "li")
        ultimo_li = li_secciones[-1]
        ultimo_li.click()
        time.sleep(0.7)

        # Seleccionamos toda la geografía, todas las tipologías penales y todos los periodosç
        # Después, clicamos en "consultar selección"
        botones_seleccionar_todas_las_opciones = browser.find_elements(By.CSS_SELECTOR, "button.icoSeleccionTodos")
        browser.execute_script("arguments[0].scrollIntoView({block:'center'});", botones_seleccionar_todas_las_opciones[0])
        time.sleep(0.7)

        #En este caso, en vez de seleccionar las opciones manualmente como hago en la otra funcion, esta vez puedo darle a 3 botones de "seleccionar todo"

        for boton in botones_seleccionar_todas_las_opciones:
            boton.click()
            time.sleep(0.7)

        boton_consultar_seleccion_datos_criminalidad = browser.find_element(By.CSS_SELECTOR, "div#capaBotones input#botonConsulSele")
        browser.execute_script("arguments[0].scrollIntoView({block:'center'});", boton_consultar_seleccion_datos_criminalidad)
        time.sleep(0.7)
        boton_consultar_seleccion_datos_criminalidad.click()
        
        WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.ID, "tablaDatosPx")))

        html_tabla_criminalidad_x_trimestre = browser.find_element(By.ID, "tablaDatosPx").get_attribute("outerHTML")
        tabla_con_datos_criminalidad_x_trimestre = BeautifulSoup(html_tabla_criminalidad_x_trimestre, "html.parser")
        table = tabla_con_datos_criminalidad_x_trimestre.find("table", id="tablaDatosPx")
        df_tabla_final = pd.read_html(str(table), header=0, decimal=",", thousands=".")[0]

        
        df_tabla_final_parseada = reestructurar_excel_datos_criminalidad(df_tabla_final, trimestre = dict_trimestres[i])
        df_tabla_final_parseada.to_excel(path + fr"\{dict_trimestres[i].lower()}_datos_criminalidad_espana.xlsx")

    browser.close()
    print("Se ha completado la obtencion de los datos de criminalidad del ministerio de interior")

def agrupar_datos_por_trimestres(df_enero_marzo, df_enero_junio, df_enero_septiembre, df_enero_diciembre):
    """ Con esta funcion pretendo agrupar todos los datos obtenidos de enero_marzo, enero_junio, enero_septiembre y enero_diciembre
        Los datos obtenidos del ministerio de interior de criminalidad, en vez de venir agrupados por trimestres, agrupan el trimestre actual
        y el trimestre anterior. De tal forma que cuando antes obtenia el dato de los botones primer trimestre, segundo trimestre... en realidad
        estaba obtiendo el agregado hasta la fecha."""
    
    cols_clave = ["Comunidad", "Provincia", "Municipio", "Tipo Delito"]

    for df in [df_enero_marzo, df_enero_junio, df_enero_septiembre, df_enero_diciembre]:
        df["Dato 2023"] = pd.to_numeric(df["Dato 2023"], errors="coerce")
        df["Dato 2022"] = pd.to_numeric(df["Dato 2022"], errors="coerce")
        for col in cols_clave:
            df[col] = df[col].fillna("").str.strip() #.str.upper()
    
    combinaciones = set()
    for df in [df_enero_marzo, df_enero_junio, df_enero_septiembre, df_enero_diciembre]:
        combinaciones.update([tuple(x) for x in df[cols_clave].values])

    def alinear(df):
        df_full = pd.DataFrame(list(combinaciones), columns=cols_clave)
        df_merge = df_full.merge(df, on=cols_clave, how="left")
        df_merge[["Dato 2023", "Dato 2022"]] = df_merge[["Dato 2023", "Dato 2022"]].fillna(0)
        return df_merge
    
    df_enero_marzo = alinear(df_enero_marzo)
    df_enero_junio = alinear(df_enero_junio)
    df_enero_septiembre = alinear(df_enero_septiembre)
    df_enero_diciembre = alinear(df_enero_diciembre)

    # Calcular trimestres reales
    df1 = df_enero_marzo.copy(); df1["Trimestre"] = "Enero-Marzo"
    df2 = df_enero_junio.copy(); df2["Dato 2023"] -= df_enero_marzo["Dato 2023"]; df2["Dato 2022"] -= df_enero_marzo["Dato 2022"]; df2["Trimestre"] = "Abril-Junio"
    df3 = df_enero_septiembre.copy(); df3["Dato 2023"] -= df_enero_junio["Dato 2023"]; df3["Dato 2022"] -= df_enero_junio["Dato 2022"]; df3["Trimestre"] = "Julio-Septiembre"
    df4 = df_enero_diciembre.copy(); df4["Dato 2023"] -= df_enero_septiembre["Dato 2023"]; df4["Dato 2022"] -= df_enero_septiembre["Dato 2022"]; df4["Trimestre"] = "Octubre-Diciembre"

    # Concatenar todos los trimestres
    df_long = pd.concat([df1, df2, df3, df4], ignore_index=True)

    ccaa_dict = {"ANDALUCÍA": "Andalucía", "ARAGÓN": "Aragón", "ASTURIAS (PRINCIPADO DE)": "Principado de Asturias", "BALEARS (ILLES)": "Illes Balears", "CANARIAS": "Canarias", 
                 "CANTABRIA": "Cantabria", "CASTILLA - LA MANCHA": "Castilla-La Mancha", "CASTILLA Y LEON": "Castilla y León", "CATALUÑA": "Cataluña", "CIUDAD AUTÓNOMA DE CEUTA": "Ciudad Autónoma de Ceuta", 
                 "CIUDAD AUTÓNOMA DE MELILLA": "Ciudad Autónoma de Melilla", "COMUNITAT VALENCIANA": "Comunidad Valenciana", "EXTREMADURA": "Extremadura", "GALICIA": "Galicia", 
                 "MADRID (COMUNIDAD DE)": "Comunidad de Madrid", "MURCIA (REGION DE)": "Región de Murcia", "NAVARRA (COMUNIDAD FORAL DE)": "Comunidad Foral de Navarra", "PAÍS VASCO": "País Vasco", 
                 "RIOJA (LA)": "La Rioja", "NACIONAL": "Nacional", "EN EL EXTRANJERO": "En el extranjero"}
    
    provincias_dict = {"Provincia de ÁVILA": "Ávila", "Provincia de ALBACETE": "Albacete", "Provincia de ALICANTE/ALACANT": "Alicante", "Provincia de ALMERÍA": "Almería", 
                       "Provincia de ARABA/ÁLAVA": "Álava", "Provincia de BADAJOZ": "Badajoz", "Provincia de BALEARS (LAS)": "Las Palmas", "Provincia de BARCELONA": "Barcelona", 
                       "Provincia de BIZKAIA": "Bizkaia", "Provincia de BURGOS": "Burgos", "Provincia de CÁCERES": "Cáceres", "Provincia de CÁDIZ": "Cádiz", "Provincia de CASTELLÓN/CASTELLÓ": "Castellón", 
                       "Provincia de CIUDAD REAL": "Ciudad Real", "Provincia de CÓRDOBA": "Córdoba", "Provincia de CORUÑA (A)": "A Coruña", "Provincia de CUENCA": "Cuenca", 
                       "Provincia de GIRONA": "Girona", "Provincia de GRANADA": "Granada", "Provincia de GUADALAJARA": "Guadalajara", "Provincia de GIPUZKOA": "Gipuzkoa", 
                       "Provincia de HUELVA": "Huelva", "Provincia de HUESCA": "Huesca", "Provincia de JAÉN": "Jaén", "Provincia de LEÓN": "León", "Provincia de LLEIDA": "Lleida", 
                       "Provincia de LUGO": "Lugo", "Provincia de MADRID": "Madrid", "Provincia de MÁLAGA": "Málaga", "Provincia de MURCIA": "Murcia", "Provincia de OURENSE": "Ourense", 
                       "Provincia de PALENCIA": "Palencia", "Provincia de PALMAS (LAS)": "Las Palmas", "Provincia de PONTEVEDRA": "Pontevedra", "Provincia de SALAMANCA": "Salamanca", 
                       "Provincia de SANTA CRUZ DE TENERIFE": "Santa Cruz de Tenerife", "Provincia de SEGOVIA": "Segovia", "Provincia de SEVILLA": "Sevilla", "Provincia de SORIA": "Soria", 
                       "Provincia de TARRAGONA": "Tarragona", "Provincia de TERUEL": "Teruel", "Provincia de TOLEDO": "Toledo", "Provincia de VALENCIA/VALÈNCIA": "Valencia", 
                       "Provincia de VALLADOLID": "Valladolid", "Provincia de ZAMORA": "Zamora", "Provincia de ZARAGOZA": "Zaragoza", "": ""}
    
    df_long["Comunidad"] = df_long["Comunidad"].replace(ccaa_dict)
    df_long["Provincia"] = df_long["Provincia"].replace(provincias_dict)
    df_long["Municipio"] = df_long["Municipio"].str.replace("Municipio de ", "", regex=False).str.replace("Municipo de ", "", regex=False)
    df_long["Variación 2023/2022"] = ((df_long["Dato 2023"] - df_long["Dato 2022"]) / df_long["Dato 2022"] * 100).round(1)

    # Pivot para 2023
    df_wide_2023 = df_long.pivot_table(index=cols_clave,columns="Trimestre",values="Dato 2023",aggfunc="first")

    # Pivot para 2022
    df_wide_2022 = df_long.pivot_table(index=cols_clave,columns="Trimestre",values="Dato 2022",aggfunc="first")

    df_variacion_2023_2022 = df_long.pivot_table(index=cols_clave, columns="Trimestre", values="Variación 2023/2022", aggfunc="first")

    df_wide_2023.columns = [f"{c}2023" for c in df_wide_2023.columns]
    df_wide_2022.columns = [f"{c}2022" for c in df_wide_2022.columns]
    df_variacion_2023_2022.columns = [f"{c}_VAR_2023_2022" for c in df_variacion_2023_2022.columns]

    df_wide = (df_wide_2023.join(df_wide_2022, how="outer").join(df_variacion_2023_2022, how="outer").reset_index())

    # Columnas de trimestres
    trimestres = ["Enero-Marzo", "Abril-Junio", "Julio-Septiembre", "Octubre-Diciembre"]

    # Sumar los trimestres para 2023 y 2022
    df_wide["Total_2023"] = df_wide[[f"{t}2023" for t in trimestres]].sum(axis=1)
    df_wide["Total_2022"] = df_wide[[f"{t}2022" for t in trimestres]].sum(axis=1)

    # Variación porcentual anual
    df_wide["Variación_total_2023_2022"] = ((df_wide["Total_2023"] - df_wide["Total_2022"]) / df_wide["Total_2022"] * 100).round(1)


    return df_long, df_wide


if __name__ == "__main__":


    ################
    ## IMPORTANTE ##
    ################

    #Para este ejercicio se asume que en el path de ejecucion, existe una carpeta data desde el inicio. Aqui es donde se van a almacenar los datos finales.
    path_ejecucion = os.getcwd()
    path = path_ejecucion + "\\data\\"


    #Llamamos a la funcion que realiza el scraping a la pagina del ministerio de interior para los datos de criminalidad
    obtener_datos_ine_criminalidad(path)
    
    #Una vez obtenidos los datos, necesitamos agruparlos para mayor comodidad de cara a la parte de streamlit
    df_enero_marzo = pd.read_excel(fr"{path}\enero_marzo_datos_criminalidad_espana.xlsx")
    df_enero_junio = pd.read_excel(fr"{path}\enero_junio_datos_criminalidad_espana.xlsx")
    df_enero_septiembre = pd.read_excel(fr"{path}\enero_septiembre_datos_criminalidad_espana.xlsx")
    df_enero_diciembre = pd.read_excel(fr"{path}\enero_diciembre_datos_criminalidad_espana.xlsx")

    long, datos_finales_criminalidad = agrupar_datos_por_trimestres(df_enero_marzo, df_enero_junio, df_enero_septiembre, df_enero_diciembre)

    # Esto es necesario porque en los datos, las comunidades autonomas que no tienen mas de 1 provincia, no aparece la combinacion Comunidad, Provincia por razones obvias.
    # Pero esto es un problema de cara a pintar los datos en nuestro futuro mapa interactivo. Es necesario que aparezca el nombre exacto de la provincia.
    # Por ejemplo, la Comunidad de Madrid está formada por una única provincia, que es Madrid. Dentro de Madrid provincia, tenemos Madrid como municipio(pero eso si que está bien reflejado).
    # Por tanto lo unico que se necesita hacer es 1. identificar las comunidades con una unica provincia e introducir el dato utilizando una mascara booleana
    mapa_comunidad_provincia = {'Cantabria': 'Cantabria', 'Comunidad Foral de Navarra': 'Navarra', 'Comunidad de Madrid': 'Madrid', 
                                'Illes Balears': 'Baleares', 'La Rioja': 'La Rioja', 'Principado de Asturias': 'Asturias', 'Región de Murcia': 'Murcia'}

    mask_long = (long["Provincia"] == "") & (long["Comunidad"].isin(mapa_comunidad_provincia.keys()))
    long.loc[mask_long, "Provincia"] = long.loc[mask_long, "Comunidad"].map(mapa_comunidad_provincia)

    mask = (datos_finales_criminalidad["Provincia"] == "") & (datos_finales_criminalidad["Comunidad"].isin(mapa_comunidad_provincia.keys()))
    datos_finales_criminalidad.loc[mask, "Provincia"] = datos_finales_criminalidad.loc[mask, "Comunidad"].map(mapa_comunidad_provincia)


    #Ahora almacenamos el dato final de criminalidad. Tanto en versión long como wide (en caso de necesitar ambas en Streamlit)
    long.to_excel(path + "datos_criminalidad_espana_LONG.xlsx")
    datos_finales_criminalidad.to_excel(path + "datos_criminalidad_espana_WIDE.xlsx")
    print(datos_finales_criminalidad.columns)


    #Llamamos a la funcion que realiza el scraping a la pagina del INE para los datos de renta media y mediana
    obtener_datos_ine_rentas(path)

        