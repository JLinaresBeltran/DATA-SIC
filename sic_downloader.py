import requests
import json
import os
import time
import re
from bs4 import BeautifulSoup
import urllib.parse
import random

class SICDownloader:
    def __init__(self, output_dir="documentos_sic"):
        """Inicializa el descargador de documentos SIC"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Lista de User-Agents comunes para simular diferentes navegadores
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(user_agents),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": "https://relatoria.sic.gov.co/",
            "Origin": "https://relatoria.sic.gov.co",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Connection": "keep-alive"
        })
        
        # Inicializar cookies visitando primero la página principal
        self._inicializar_sesion()
    
    def _inicializar_sesion(self):
        """Visita la página principal para obtener cookies iniciales"""
        try:
            print("Inicializando sesión con la SIC...")
            response = self.session.get("https://relatoria.sic.gov.co/")
            if response.status_code == 200:
                print("✓ Sesión inicializada correctamente")
            else:
                print(f"× Error al inicializar sesión: {response.status_code}")
        except Exception as e:
            print(f"× Error al inicializar sesión: {e}")

    def buscar_documentos(self, terminos_busqueda, size=20, from_index=0):
        """Realiza una búsqueda en el índice de relatorías"""
        print(f"Buscando documentos para: '{terminos_busqueda}'")
        
        # Base URL para la búsqueda
        base_url = "https://relatoria.sic.gov.co/sic-relatoria-idx/_search"
        
        # Construir la consulta (version simple para evitar errores de encoding)
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": terminos_busqueda,
                                "fields": [
                                    "informacion.ano_expediente^9",
                                    "informacion.numero_expediente^10",
                                    "informacion.tipo_proceso^2",
                                    "informacion.tipo_providencia^2",
                                    "tesauro.categoria.nombre^5",
                                    "tesauro.descriptor.nombre^6",
                                    "tesauro.restrictor.nombre^8",
                                    "partes.nombre^3",
                                    "partes.numero_doc",
                                    "archivos.contenido_archivo^1.5",
                                    "archivos.entidades.texto^1.5",
                                    "documento_resumen.transcripcion^1.5"
                                ],
                                "default_operator": "AND"
                            }
                        }
                    ],
                    "should": [
                        {
                            "match": {
                                "tesauro.categoria.nombre": {
                                    "query": terminos_busqueda
                                }
                            }
                        },
                        {
                            "match": {
                                "tesauro.descriptor.nombre": {
                                    "query": terminos_busqueda
                                }
                            }
                        },
                        {
                            "match": {
                                "tesauro.restrictor.nombre": {
                                    "query": terminos_busqueda,
                                    "boost": 3
                                }
                            }
                        }
                    ],
                    "filter": []
                }
            },
            "size": size,
            "from": from_index,
            "highlight": {
                "fields": {
                    "archivos.contenido_archivo": {},
                    "informacion.numero_expediente": {},
                    "informacion.tipo_proceso": {},
                    "informacion.tipo_providencia": {},
                    "tesauro.categoria.nombre": {},
                    "tesauro.descriptor.nombre": {},
                    "tesauro.restrictor.nombre": {},
                    "partes.nombre": {},
                    "partes.numero_doc": {},
                    "archivos.entidades.texto": {},
                    "documento_resumen.transcripcion": {}
                }
            }
        }
        
        # Primer intento: enviar la consulta como JSON en el cuerpo de la solicitud
        try:
            headers = self.session.headers.copy()
            headers.update({
                "Content-Type": "application/json"
            })
            
            # Enfoque 1: Usar POST con cuerpo JSON
            response = self.session.post(
                "https://relatoria.sic.gov.co/sic-relatoria-idx/_search",
                json=query,
                headers=headers
            )
            
            if response.status_code == 200:
                print("✓ Búsqueda exitosa (método POST)")
                return response.json()
            else:
                print(f"× Error en búsqueda POST: {response.status_code}")
            
            # Enfoque 2: Usar GET con parámetros en URL
            params = {
                "source": json.dumps(query),
                "source_content_type": "application/json"
            }
            
            response = self.session.get(base_url, params=params, headers=headers)
            
            if response.status_code == 200:
                print("✓ Búsqueda exitosa (método GET)")
                return response.json()
            else:
                print(f"× Error en búsqueda GET: {response.status_code}")
                
            # Enfoque 3: Usar la forma que vimos en el navegador
            print("Intentando método alternativo de búsqueda...")
            
            # Esta URL simula exactamente lo que vimos en los logs del navegador
            search_url = f"https://relatoria.sic.gov.co/#/results?q={urllib.parse.quote(terminos_busqueda)}"
            
            # Primero visitamos la página de resultados para obtener posibles tokens
            response = self.session.get(search_url)
            if response.status_code == 200:
                print("✓ Visita a página de resultados exitosa")
                
                # Esperar brevemente para simular comportamiento humano
                time.sleep(2)
                
                # Ahora intentamos la búsqueda en la API como lo haría el navegador
                api_url = "https://relatoria.sic.gov.co/api/v1/busqueda"
                api_payload = {
                    "terminos": terminos_busqueda,
                    "pagina": 1,
                    "resultados_pagina": size
                }
                
                api_response = self.session.post(api_url, json=api_payload)
                if api_response.status_code == 200:
                    print("✓ Búsqueda exitosa (API alternativa)")
                    return api_response.json()
                else:
                    print(f"× Error en API alternativa: {api_response.status_code}")
            
            print("⚠ Todos los métodos de búsqueda fallaron. Intentando simulación de navegador...")
            return self._buscar_con_simulacion(terminos_busqueda, size)
            
        except Exception as e:
            print(f"× Error en la búsqueda: {e}")
            return None
    
    def _buscar_con_simulacion(self, terminos_busqueda, size=20):
        """Simula la navegación manual para extraer resultados"""
        try:
            # Visitar la página principal primero
            self.session.get("https://relatoria.sic.gov.co/")
            time.sleep(1)
            
            # Visitar la página de resultados
            url_resultados = f"https://relatoria.sic.gov.co/#/results?q={urllib.parse.quote(terminos_busqueda)}"
            response = self.session.get(url_resultados)
            
            if response.status_code != 200:
                print(f"× Error al acceder a página de resultados: {response.status_code}")
                return None
            
            # Extraer resultados del HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar script que contenga los datos de resultados
            scripts = soup.find_all('script')
            resultados_data = None
            
            for script in scripts:
                if script.string and "window.__INITIAL_STATE__" in script.string:
                    # Extraer el JSON de los resultados
                    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script.string, re.DOTALL)
                    if match:
                        try:
                            resultados_data = json.loads(match.group(1))
                            break
                        except:
                            pass
            
            if resultados_data:
                print("✓ Datos extraídos de la página HTML")
                return resultados_data
            else:
                print("× No se pudieron extraer resultados del HTML")
                return None
            
        except Exception as e:
            print(f"× Error en simulación de navegador: {e}")
            return None

    def obtener_ids_documentos(self, resultados):
        """Extrae los IDs de documentos y metadatos relevantes de los resultados"""
        documentos = []
        
        if not resultados or "hits" not in resultados or "hits" not in resultados["hits"]:
            return documentos
        
        for hit in resultados["hits"]["hits"]:
            doc_id = hit["_id"]  # ID del documento en Elasticsearch
            source = hit["_source"]
            
            # Extraer información básica
            info = source.get("informacion", {})
            año = info.get("ano_expediente", "")
            numero = info.get("numero_expediente", "")
            tipo_providencia = info.get("tipo_providencia", "")
            fecha = info.get("fecha_providencia", "")
            
            # Extraer partes involucradas
            partes = source.get("partes", [])
            nombres_partes = [parte.get("nombre", "") for parte in partes]
            
            # Extraer información de archivos disponibles
            archivos = source.get("archivos", [])
            archivo_info = []
            for archivo in archivos:
                archivo_info.append({
                    "tipo": archivo.get("tipo_archivo", ""),
                    "path_s3": archivo.get("path_s3", "")
                })
            
            # Información de tesauro
            tesauro = source.get("tesauro", {})
            categorias = [cat.get("nombre", "") for cat in tesauro.get("categoria", [])]
            descriptores = [desc.get("nombre", "") for desc in tesauro.get("descriptor", [])]
            
            # Obtener resumen si existe
            resumen = source.get("documento_resumen", {}).get("transcripcion", "")
            
            documentos.append({
                "id": doc_id,
                "año": año,
                "numero": numero,
                "tipo_providencia": tipo_providencia,
                "fecha": fecha,
                "partes": nombres_partes,
                "archivos": archivo_info,
                "categorias": categorias,
                "descriptores": descriptores,
                "resumen": resumen
            })
        
        return documentos

    def obtener_url_visor_relatorias(self, doc_id, tipo_archivo="Sentencia_escrita"):
        """Genera la URL correcta para acceder al visor de relatorías"""
        base_url = "https://gestor.relatoria.sic.gov.co/visor-relatorias"
        url = f"{base_url}/{doc_id}/archivos-providencia/{tipo_archivo}"
        return url

    def extraer_links_documentos(self, url_visor):
        """Extrae los enlaces a los documentos desde la página del visor"""
        print(f"Analizando: {url_visor}")
        
        # Actualizar el Referer para esta solicitud
        headers = self.session.headers.copy()
        headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
        })
        
        try:
            response = self.session.get(url_visor, headers=headers)
            response.raise_for_status()
            
            # Parsear el HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Búsqueda de enlaces y elementos relevantes
            links = []
            
            # 1. Buscar enlaces directos a documentos
            pdf_links = soup.find_all('a', href=re.compile(r'\.(pdf|docx?|xlsx?)$', re.I))
            for link in pdf_links:
                href = link.get('href')
                if href and href not in links:
                    # Convertir URL relativa a absoluta si es necesario
                    if not href.startswith(('http://', 'https://')):
                        href = urllib.parse.urljoin(url_visor, href)
                    links.append(href)
            
            # 2. Buscar en contenedores de documentos
            content_containers = soup.find_all(['div', 'section'], class_=re.compile(r'(documento|archivo|file|document|content)', re.I))
            for container in content_containers:
                anchors = container.find_all('a')
                for anchor in anchors:
                    href = anchor.get('href')
                    if href and href not in links:
                        if not href.startswith(('http://', 'https://')):
                            href = urllib.parse.urljoin(url_visor, href)
                        links.append(href)
            
            # 3. Buscar en iframes
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src and src not in links:
                    if not src.startswith(('http://', 'https://')):
                        src = urllib.parse.urljoin(url_visor, src)
                    links.append(src)
            
            # 4. Buscar en scripts (URLs embebidas)
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Buscar URLs en el contenido del script
                    url_matches = re.findall(r'(https?://[^\s"\'<>]+\.(pdf|docx?|xlsx?|zip))', script.string)
                    for url_match, _ in url_matches:
                        if url_match not in links:
                            links.append(url_match)
                    
                    # Buscar URLs en formato AWS S3
                    s3_matches = re.findall(r'(https?://[^\s"\'<>]+amazonaws\.com[^\s"\'<>]+)', script.string)
                    for s3_url in s3_matches:
                        if s3_url not in links:
                            links.append(s3_url)
            
            print(f"Se encontraron {len(links)} enlaces.")
            return links
        
        except requests.exceptions.RequestException as e:
            print(f"Error al acceder al visor: {e}")
            return []

    def obtener_url_s3(self, path_s3):
        """Obtiene la URL firmada para un archivo en S3"""
        if not path_s3:
            return None
        
        # Base URL para obtener la URL firmada
        base_url = "https://m0s03uyzg3.execute-api.us-east-1.amazonaws.com/prod/get-signed-url/"
        
        # Codificar la ruta S3 en la URL
        url = base_url + urllib.parse.quote(path_s3)
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("url")  # URL firmada
        except requests.exceptions.RequestException as e:
            print(f"Error al obtener URL firmada: {e}")
            return None

    def descargar_documento(self, url, nombre_archivo):
        """Descarga un documento dado su URL"""
        # Verificar si ya existe
        if os.path.exists(nombre_archivo):
            print(f"El archivo ya existe: {nombre_archivo}")
            return True
        
        # Actualizar headers para la descarga
        headers = self.session.headers.copy()
        headers.update({
            "Accept": "*/*"
        })
        
        try:
            print(f"Descargando: {nombre_archivo}")
            response = self.session.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            # Guardar el archivo
            with open(nombre_archivo, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"✓ Documento descargado: {nombre_archivo}")
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"× Error al descargar documento: {e}")
            return False

    def procesar_documentos(self, terminos_busqueda, max_documentos=None, tipos_archivo=None):
        """Procesa todos los documentos para los términos de búsqueda dados"""
        if tipos_archivo is None:
            tipos_archivo = ["Sentencia_escrita", "Auto_escrito", "Sentencia_oral", "Comunicacion"]
        
        # Realizar la búsqueda inicial
        resultados = self.buscar_documentos(terminos_busqueda)
        if not resultados:
            print("No se encontraron resultados para la búsqueda.")
            return
        
        # Extraer IDs y metadatos
        documentos = self.obtener_ids_documentos(resultados)
        
        # Limitar número de documentos si es necesario
        if max_documentos:
            documentos = documentos[:max_documentos]
        
        print(f"\nProcesando {len(documentos)} documentos encontrados...")
        print("-" * 80)
        
        # Contador de documentos descargados
        total_descargados = 0
        
        # Procesar cada documento
        for i, doc in enumerate(documentos, 1):
            doc_id = doc["id"]
            año = doc["año"]
            numero = doc["numero"]
            tipo_prov = doc["tipo_providencia"]
            
            # Nombre base para los archivos
            base_nombre = f"{año}_{numero}_{tipo_prov}"
            
            print(f"\n[{i}/{len(documentos)}] Documento: {base_nombre} (ID: {doc_id})")
            print("  Partes:", ", ".join(doc["partes"]) if doc["partes"] else "N/A")
            print("  Descriptores:", ", ".join(doc["descriptores"]) if doc["descriptores"] else "N/A")
            
            # 1. Primero intentar descargar archivos desde S3 si están disponibles
            s3_descargados = 0
            for j, archivo in enumerate(doc["archivos"], 1):
                path_s3 = archivo.get("path_s3")
                tipo_archivo = archivo.get("tipo")
                
                if path_s3:
                    print(f"  - Archivo S3 #{j}: {tipo_archivo} ({path_s3})")
                    url_s3 = self.obtener_url_s3(path_s3)
                    
                    if url_s3:
                        # Determinar extensión
                        extension = "pdf"  # Por defecto PDF
                        if path_s3.lower().endswith(".docx"):
                            extension = "docx"
                        elif path_s3.lower().endswith(".doc"):
                            extension = "doc"
                        
                        # Crear nombre de archivo
                        nombre_archivo = os.path.join(self.output_dir, f"{base_nombre}_{tipo_archivo.replace(' ', '_')}.{extension}")
                        
                        # Descargar
                        if self.descargar_documento(url_s3, nombre_archivo):
                            s3_descargados += 1
                            total_descargados += 1
                
                # Espaciar las solicitudes
                time.sleep(0.5)
            
            if s3_descargados > 0:
                print(f"  ✓ Descargados {s3_descargados} archivos desde S3.")
            else:
                print("  × No se encontraron archivos disponibles en S3.")
            
            # 2. Intentar descargar documentos desde el visor de relatorías
            visor_descargados = 0
            
            for tipo in tipos_archivo:
                # Generar URL del visor
                url_visor = self.obtener_url_visor_relatorias(doc_id, tipo)
                
                # Extraer enlaces
                enlaces = self.extraer_links_documentos(url_visor)
                
                # Descargar documentos encontrados
                for j, enlace in enumerate(enlaces, 1):
                    # Determinar tipo de archivo
                    extension = "pdf"  # Por defecto PDF
                    if enlace.lower().endswith(".docx"):
                        extension = "docx"
                    elif enlace.lower().endswith(".doc"):
                        extension = "doc"
                    elif enlace.lower().endswith(".xlsx"):
                        extension = "xlsx"
                    elif enlace.lower().endswith(".xls"):
                        extension = "xls"
                    
                    # Crear nombre de archivo
                    nombre_archivo = os.path.join(self.output_dir, f"{base_nombre}_{tipo.replace(' ', '_')}_{j}.{extension}")
                    
                    # Descargar
                    if self.descargar_documento(enlace, nombre_archivo):
                        visor_descargados += 1
                        total_descargados += 1
                
                # Espaciar las solicitudes
                time.sleep(1)
            
            if visor_descargados > 0:
                print(f"  ✓ Descargados {visor_descargados} documentos desde el visor.")
            else:
                print("  × No se encontraron documentos descargables en el visor.")
            
            # Esperar entre documentos para no sobrecargar el servidor
            time.sleep(2)
        
        print("\n" + "=" * 80)
        print(f"Resumen: Se procesaron {len(documentos)} documentos y se descargaron {total_descargados} archivos.")
        print("Los archivos se encuentran en el directorio:", os.path.abspath(self.output_dir))
        print("=" * 80)

# Función principal para ejecutar desde línea de comandos
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Descargador de documentos de la SIC.')
    parser.add_argument('terminos', help='Términos de búsqueda')
    parser.add_argument('--max', type=int, default=None, help='Número máximo de documentos a procesar')
    parser.add_argument('--dir', default='documentos_sic', help='Directorio de salida')
    
    args = parser.parse_args()
    
    # Inicializar el descargador
    downloader = SICDownloader(output_dir=args.dir)
    
    # Procesar documentos
    downloader.procesar_documentos(
        terminos_busqueda=args.terminos,
        max_documentos=args.max
    )

if __name__ == "__main__":
    main()