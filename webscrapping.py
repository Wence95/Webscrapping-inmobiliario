from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException
import mysql.connector as con
import pandas as pd
import time

OPERACIONES = ["Venta", "Arriendo"]
PROPIEDADES = ["Departamentos", "Casas"]
BUSQUEDA = "Punta Arenas"

driver = webdriver.Chrome(service=Service("chromedriver-win64/chromedriver.exe"))

#se setea el tiempo de espera implicito a 2 segundos
driver.implicitly_wait(2)

data_list = []

for operacion in OPERACIONES:
    for propiedad in PROPIEDADES:

        driver.get("https://www.portalinmobiliario.com/")

        time.sleep(3)

        #se busca botón por aria-label
        element = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Tipo de operación']")
        element.click()

        #esperar a que aparezca lista de operaciones
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul[aria-label='Tipo de operación']")))

        #se crea una lista el texto en los span de la lista de operaciones
        element = driver.find_element(By.CSS_SELECTOR, "ul[aria-label='Tipo de operación']")
        elements = element.find_elements(By.TAG_NAME, "span")
        for element in elements:
            #si el elemento está en la lista de operaciones, se hace click
            if element.text == operacion:
                element.click()
                break

        #se busca botón por aria-label
        element = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Tipo de propiedad']")
        element.click()

        #esperar a que aparezca lista de propiedades
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul[aria-label='Tipo de propiedad']")))

        #se crea una lista el texto en los span de la lista de propiedades
        element = driver.find_element(By.CSS_SELECTOR, "ul[aria-label='Tipo de propiedad']")
        elements = element.find_elements(By.TAG_NAME, "span")
        for element in elements:
            #si el elemento está en la lista de propiedad, se hace click
            if element.text == propiedad:
                element.click()
                break

        #se busca el input de ciudad a partir de su placeholder, el cual debe tener la palabra ciudad, y se escribe Punta Arenas

        element = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='ciudad']")

        element.send_keys(BUSQUEDA)

        #esperar a que aparezca lista de locaciones
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "LOCATION-list")))

        #se presiona el primer botón de la lista (ul) que aparece cuya id es LOCATION-list

        element = driver.find_element(By.ID, "LOCATION-list")
        element.find_element(By.TAG_NAME, "button").click()

        time.sleep(2)

        #se busca el botón cuyo span tiene texto dice "buscar" y se hace click
        elements = driver.find_elements(By.CSS_SELECTOR, "button span")
        for element in elements:
            if element.text == "Buscar":
                element.click()
                break

        #si existe el link "siguiente" se hace click y se repite el proceso
        url_list = []
        while True:
            try:
                #esperar hasta que aparezca la sección con clase ui-search-layout ui-search-layout--grid
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "ui-search-results")))

                #obtener los elementos 'a' dentro de la seccion buscada y guardar los links en un arreglo (ignorando repetidos y urls que contengan '/tienda-oficial/')
                element = driver.find_element(By.CLASS_NAME, "ui-search-layout.ui-search-layout--grid")
                elements = element.find_elements(By.CLASS_NAME, "ui-search-result__content.no-borders")

                print(len(elements))
                
                #se setea la espera implícita a 0, ya que llegado a este punto, la página ya está cargada
                driver.implicitly_wait(0)

                for element in elements:
                    link = element.find_element(By.TAG_NAME, "a")
                    if link.get_attribute("href") not in url_list and "/tienda-oficial/" not in link.get_attribute("href"):
                        try:
                            label = element.find_element(By.CLASS_NAME, "ui-search-styled-label.ui-search-item__highlight-label__text").text
                            if label == "PROYECTO":
                                continue
                        except NoSuchElementException:
                            pass
                        url_list.append(link.get_attribute("href"))
                #volvemos a setear la espera implícita a 2 segundos
                driver.implicitly_wait(2)
                element = driver.find_element(By.CLASS_NAME, "andes-pagination__button.andes-pagination__button--next")
                element = element.find_element(By.TAG_NAME, "a")
                driver.execute_script("arguments[0].scrollIntoView(true);", element)
                element.click()

            except NoSuchElementException:
                break
            except ElementNotInteractableException:
                break

        #visitar cada una de las urls y obtener los datos de la propiedad
        for url in url_list:
            print(url)
            while(True):
                driver.get(url)
                #a veces la página redirecciona a mercado libre, nos aseguramos de que estamos en la página a la que queremos ir
                if driver.current_url == url:
                    break            
            data = {}
            data['url'] = url.split("#")[0]
            element = driver.find_element(By.CLASS_NAME, "ui-vpp-denounce")
            element = element.find_element(By.CLASS_NAME, "ui-pdp-color--BLACK.ui-pdp-family--SEMIBOLD")
            data['ID'] = element.text.split("#")[1]
            data['Operacion'] = operacion
            data['Propiedad'] = propiedad
            data['Titulo'] = driver.find_element(By.CLASS_NAME, "ui-pdp-title").text
            #buscar ui-pdp-price__second-line
            element = driver.find_element(By.CLASS_NAME, "ui-pdp-price__second-line")

            data['Currency'] = element.find_element(By.CLASS_NAME, "andes-money-amount__currency-symbol").text
            if data['Currency'] == "$":
                data['Currency'] = "CLP"
            data['Precio'] = element.find_element(By.CLASS_NAME, "andes-money-amount__fraction").text.replace(".", "").replace(",", ".")
            
            #este dato no siempre está presente, por lo que se maneja la excepción
            try:
                element = driver.find_element(By.CLASS_NAME, "ui-pdp-media.ui-vip-location__subtitle.ui-pdp-color--BLACK")
                data['Ubicacion'] = element.find_element(By.TAG_NAME, "p").text
            except:
                data['Ubicacion'] = ""

            #esperar a que sea cliqueable el elemento
            element = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "ui-pdp-collapsable__action"))
            )

            #scroll para ver el elemento y cliquear
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()

            #esperar a que aparezca la tabla con los datos
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "ui-vpp-striped-specs__table")))
            element = driver.find_element(By.CLASS_NAME, "ui-vpp-striped-specs__table")
            #crear un nuevo diccionario con elementos de la tabla, que tiene 2 columnas, la primera es la llave y la segunda el valor
            elements = element.find_elements(By.CLASS_NAME, "andes-table__row.ui-vpp-striped-specs__row")
            dict_data = {}
            for element in elements:
                key = element.find_element(By.TAG_NAME, "th").text
                value = element.find_element(By.TAG_NAME, "td").text
                dict_data[key] = value
            data['Antiguedad'] = dict_data.get("Antigüedad", "").replace(" años", "")
            data['Superficie total'] = dict_data.get("Superficie total", "").replace(".", "").replace(",", ".").replace(" m²", "")
            data['Superficie útil'] = dict_data.get("Superficie útil", "").replace(".", "").replace(",", ".").replace(" m²", "")
            data['Dormitorios'] = dict_data.get("Dormitorios", "")
            data['Baños'] = dict_data.get("Baños", "")
            
            data_list.append(data)

driver.quit()

df = pd.DataFrame(data_list)

#se abre un archivo csv con datos anteriores en caso de que exista
try:
    df_csv = pd.read_csv("inmobiliaria.csv", sep=";")
except:
    df_csv = pd.DataFrame()

df_csv["ID"] = df_csv["ID"].astype(str)

#se concatenan ambos dataframes y se eliminan duplicados
merged_df = pd.concat([df, df_csv], ignore_index=True)
merged_df.drop_duplicates(subset=['ID'], inplace=True)

#se guarda el dataframe en un archivo csv
merged_df.to_csv("inmobiliaria.csv", index=False, sep=";")

cnx = con.connect(user="pablo_b", 
                              password="Webscrap123", 
                              host="big-data-webscrapping2.mysql.database.azure.com", 
                              port=3306, 
                              database="ws_inmobiliaria")
cursor = cnx.cursor()
query = ("SELECT * FROM ws_inmobiliaria.ws_aviso;")
cursor.execute(query)
#poner data de base de datos en dataframe
data = pd.DataFrame(cursor.fetchall())
print(data)
data_to_insert = pd.read_csv("inmobiliaria.csv", sep=";")
#borrar filas que ya existen
try:
    data_to_insert = data_to_insert[~data_to_insert["ID"].isin(data[1])]
except:
    pass

cursor = cnx.cursor()
for _, row in data_to_insert.iterrows():
    query = """INSERT INTO ws_aviso (url, id_aviso, operacion, propiedad, titulo, currency, precio, ubicacion, 
        anhos_antiguedad, m2_superficie_total, m2_superficie_util, dormitorios, banhos) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"""
    # Convertir NaN a None
    row = row.where(pd.notnull(row), None)
    print(query, tuple(row))
    cursor.execute(query, tuple(row))
cnx.commit()
cursor.close()
cnx.close()