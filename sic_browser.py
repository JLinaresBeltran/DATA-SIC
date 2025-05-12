import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class SICBrowser:
    def __init__(self, headless=True):
        """Inicializa un navegador para acceder a la SIC"""
        # Configurar opciones de Chrome
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Configurar User-Agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36")
        
        # Iniciar el navegador
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
    
    def buscar_documentos(self, terminos_busqueda):
        """Busca documentos en el sistema de relatoria de la SIC"""
        try:
            # Visitar la página principal
            print("Navegando a la página principal de la SIC...")
            self.driver.get("https://relatoria.sic.gov.co/")
            time.sleep(3)  # Esperar a que cargue
            
            # Buscar el campo de búsqueda e ingresar los términos
            print(f"Buscando: '{terminos_busqueda}'")
            search_box = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.input_invisible")))
            search_box.clear()
            search_box.send_keys(terminos_busqueda)
            
            # Presionar la tecla Enter para buscar
            search_box.send_keys(u'\ue007')  # Código para Enter
            
            # Esperar a que aparezcan los resultados
            print("Esperando resultados...")
            time.sleep(5)  # Dar tiempo para que carguen los resultados
            
            # Capturar los resultados (el selector específico dependerá de la estructura de la página)
            try:
                resultados_container = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".resultado-container")))
                resultados_items = self.driver.find_elements(By.CSS_SELECTOR, ".resultado-item")
                
                print(f"Se encontraron {len(resultados_items)} resultados.")
                
                # Procesar los resultados
                resultados = []
                for item in resultados_items:
                    try:
                        # Extraer información básica
                        titulo = item.find_element(By.CSS_SELECTOR, ".titulo").text
                        expediente = item.find_element(By.CSS_SELECTOR, ".expediente").text if item.find_elements(By.CSS_SELECTOR, ".expediente") else ""
                        fecha = item.find_element(By.CSS_SELECTOR, ".fecha").text if item.find_elements(By.CSS_SELECTOR, ".fecha") else ""
                        
                        # Obtener el enlace al documento
                        enlace_elem = item.find_element(By.CSS_SELECTOR, "a.view-document")
                        enlace = enlace_elem.get_attribute("href")
                        
                        # Extraer ID del documento
                        doc_id = ""
                        if enlace:
                            # Extraer ID del documento de la URL
                            import re
                            id_match = re.search(r'/([^/]+)/archivos-providencia', enlace)
                            if id_match:
                                doc_id = id_match.group(1)
                        
                        resultados.append({
                            "titulo": titulo,
                            "expediente": expediente,
                            "fecha": fecha,
                            "enlace": enlace,
                            "id": doc_id
                        })
                    except Exception as e:
                        print(f"Error al procesar resultado: {e}")
                
                return resultados
                
            except TimeoutException:
                print("No se encontraron resultados o la estructura de la página es diferente.")
                return []
                
        except Exception as e:
            print(f"Error al buscar documentos: {e}")
            return []
    
    def obtener_documento(self, url_documento, ruta_destino):
        """Navega a la URL del documento y descarga el PDF"""
        try:
            print(f"Navegando a: {url_documento}")
            self.driver.get(url_documento)
            time.sleep(5)  # Esperar a que cargue
            
            # Buscar enlaces de descarga
            enlaces_descarga = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='.pdf'], a[href*='download'], button.download-btn")
            
            if enlaces_descarga:
                print(f"Se encontraron {len(enlaces_descarga)} enlaces de descarga.")
                
                # Hacer clic en el primer enlace de descarga
                enlaces_descarga[0].click()
                print("Se hizo clic en el enlace de descarga.")
                
                # Esperar a que se descargue
                time.sleep(5)
                
                # Verificar si se descargó correctamente
                # Nota: Esto depende de cómo se maneja la descarga en el sitio
                return True
            else:
                print("No se encontraron enlaces de descarga.")
                return False
            
        except Exception as e:
            print(f"Error al obtener documento: {e}")
            return False
    
    def cerrar(self):
        """Cierra el navegador"""
        if self.driver:
            self.driver.quit()
