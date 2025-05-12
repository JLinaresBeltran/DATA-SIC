import requests
from bs4 import BeautifulSoup
import time
import os
import re
import json
import urllib.parse

def buscar_documentos_sic(terminos, max_docs=10):
    """Busca documentos en la SIC y devuelve los resultados"""
    print(f"Buscando documentos para: '{terminos}'")
    
    # Configurar sesión con headers adecuados
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9",
        "Referer": "https://relatoria.sic.gov.co/",
        "Origin": "https://relatoria.sic.gov.co",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    })
    
    # Visitar la página principal primero para obtener cookies
    try:
        print("Inicializando sesión...")
        session.get("https://relatoria.sic.gov.co/")
        time.sleep(1)
        
        # Intentar primero con la API directa
        api_url = "https://relatoria.sic.gov.co/api/v1/busqueda"
        api_payload = {
            "terminos": terminos,
            "pagina": 1,
            "resultados_pagina": max_docs
        }
        
        response = session.post(api_url, json=api_payload)
        
        if response.status_code == 200:
            print("✓ Búsqueda exitosa (API)")
            data = response.json()
            return data.get("resultados", [])
        else:
            print(f"× Error en API: {response.status_code}")
        
        # Si falla, intentar con la forma de búsqueda en Elasticsearch
        search_url = "https://relatoria.sic.gov.co/sic-relatoria-idx/_search"
        query = {
            "query": {
                "query_string": {
                    "query": terminos,
                    "default_operator": "AND"
                }
            },
            "size": max_docs
        }
        
        response = session.post(search_url, json=query, headers={"Content-Type": "application/json"})
        
        if response.status_code == 200:
            print("✓ Búsqueda exitosa (Elasticsearch)")
            data = response.json()
            resultados = []
            
            for hit in data.get("hits", {}).get("hits", []):
                doc_id = hit.get("_id")
                source = hit.get("_source", {})
                info = source.get("informacion", {})
                
                resultados.append({
                    "id": doc_id,
                    "titulo": info.get("tipo_providencia", "") + " " + info.get("numero_expediente", ""),
                    "expediente": info.get("numero_expediente", ""),
                    "fecha": info.get("fecha_providencia", ""),
                    "archivos": source.get("archivos", [])
                })
            
            return resultados
        else:
            print(f"× Error en Elasticsearch: {response.status_code}")
        
        # Si ambos fallan, intentar extraer del HTML
        print("Intentando extraer resultados del HTML...")
        search_html_url = f"https://relatoria.sic.gov.co/#/results?q={urllib.parse.quote(terminos)}"
        
        response = session.get(search_html_url)
        
        if response.status_code == 200:
            # Esperar a que JavaScript cargue los resultados (solo simulación)
            time.sleep(3)
            
            # En realidad, esto no funcionará porque necesitamos un navegador real
            # para ejecutar el JavaScript. Esta parte es solo un placeholder.
            return []
        
        print("× Todos los métodos fallaron")
        return []
        
    except Exception as e:
        print(f"Error al buscar documentos: {e}")
        return []

def obtener_url_documento(doc_id, tipo="Sentencia_escrita"):
    """Genera URL para acceder al documento"""
    return f"https://gestor.relatoria.sic.gov.co/visor-relatorias/{doc_id}/archivos-providencia/{tipo}"

def obtener_url_s3(path_s3, session):
    """Obtiene URL firmada para un archivo en S3"""
    if not path_s3:
        return None
    
    base_url = "https://m0s03uyzg3.execute-api.us-east-1.amazonaws.com/prod/get-signed-url/"
    url = base_url + urllib.parse.quote(path_s3)
    
    try:
        response = session.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("url")
    except:
        pass
    
    return None

def descargar_documento(url, nombre_archivo, session):
    """Descarga un documento"""
    if os.path.exists(nombre_archivo):
        print(f"El archivo ya existe: {nombre_archivo}")
        return True
    
    try:
        print(f"Descargando: {nombre_archivo}")
        response = session.get(url, stream=True)
        
        if response.status_code == 200:
            with open(nombre_archivo, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✓ Descargado: {nombre_archivo}")
            return True
        else:
            print(f"× Error al descargar: {response.status_code}")
            return False
    except Exception as e:
        print(f"× Error: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Descargador minimalista de documentos de la SIC.')
    parser.add_argument('terminos', help='Términos de búsqueda')
    parser.add_argument('--max', type=int, default=5, help='Número máximo de documentos')
    parser.add_argument('--dir', default='documentos_sic', help='Directorio de salida')
    
    args = parser.parse_args()
    
    # Crear directorio de salida
    os.makedirs(args.dir, exist_ok=True)
    
    # Configurar sesión
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    })
    
    # Buscar documentos
    resultados = buscar_documentos_sic(args.terminos, args.max)
    
    if not resultados:
        print("No se encontraron resultados.")
        return
    
    print(f"Se encontraron {len(resultados)} documentos.")
    
    # Guardar resultados en JSON
    with open(os.path.join(args.dir, "resultados.json"), 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    
    # Procesar cada documento
    for i, doc in enumerate(resultados, 1):
        doc_id = doc.get("id", "")
        titulo = doc.get("titulo", f"documento_{i}")
        
        print(f"\n[{i}/{len(resultados)}] Procesando: {titulo}")
        
        # Intentar descargar a través de S3 si está disponible
        archivos = doc.get("archivos", [])
        descargado = False
        
        for archivo in archivos:
            path_s3 = archivo.get("path_s3")
            tipo = archivo.get("tipo_archivo", "")
            
            if path_s3:
                url_s3 = obtener_url_s3(path_s3, session)
                if url_s3:
                    nombre_archivo = os.path.join(args.dir, f"{i:02d}_{titulo.replace(' ', '_')}_{tipo}.pdf")
                    if descargar_documento(url_s3, nombre_archivo, session):
                        descargado = True
        
        # Si no se descargó por S3, intentar con el visor
        if not descargado and doc_id:
            url_visor = obtener_url_documento(doc_id)
            print(f"Intentando a través del visor: {url_visor}")
            
            # Intentar extraer enlaces del visor
            try:
                response = session.get(url_visor)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Buscar enlaces a PDFs
                    pdf_links = []
                    for a in soup.find_all('a', href=True):
                        if a['href'].endswith('.pdf'):
                            pdf_links.append(a['href'])
                    
                    # Buscar en scripts
                    for script in soup.find_all('script'):
                        if script.string:
                            pdf_matches = re.findall(r'(https?://[^\s"\'<>]+\.pdf)', script.string)
                            pdf_links.extend(pdf_matches)
                    
                    # Descargar PDFs encontrados
                    for j, pdf_link in enumerate(pdf_links, 1):
                        nombre_archivo = os.path.join(args.dir, f"{i:02d}_{titulo.replace(' ', '_')}_{j}.pdf")
                        descargar_documento(pdf_link, nombre_archivo, session)
            except Exception as e:
                print(f"Error al procesar visor: {e}")
        
        # Esperar entre documentos
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print(f"Proceso completado. Documentos guardados en: {args.dir}")
    print("=" * 50)

if __name__ == "__main__":
    main()