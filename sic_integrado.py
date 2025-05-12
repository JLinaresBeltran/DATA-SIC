import os
import sys
import time
import json
import argparse

def main():
    parser = argparse.ArgumentParser(description='Descargador de documentos de la SIC.')
    parser.add_argument('terminos', help='Términos de búsqueda')
    parser.add_argument('--max', type=int, default=None, help='Número máximo de documentos a procesar')
    parser.add_argument('--dir', default='documentos_sic', help='Directorio de salida')
    parser.add_argument('--selenium', action='store_true', help='Usar Selenium para la búsqueda')
    
    args = parser.parse_args()
    
    # Crear directorio para documentos si no existe
    os.makedirs(args.dir, exist_ok=True)
    
    # Intentar primero con el método de requests
    if not args.selenium:
        try:
            from sic_downloader import SICDownloader
            print("Intentando descarga con método de API...")
            
            downloader = SICDownloader(output_dir=args.dir)
            downloader.procesar_documentos(
                terminos_busqueda=args.terminos,
                max_documentos=args.max
            )
            
            # Verificar si se descargaron documentos
            archivos = os.listdir(args.dir)
            if not archivos:
                print("\n⚠ No se descargaron documentos con el método de API. Intentando con Selenium...")
                usar_selenium = True
            else:
                print(f"\n✓ Se descargaron {len(archivos)} documentos con éxito.")
                return
        except Exception as e:
            print(f"\n× Error con el método de API: {e}")
            print("Intentando con Selenium...")
            usar_selenium = True
    else:
        usar_selenium = True
    
    # Si falla o se especifica --selenium, usar Selenium
    if usar_selenium:
        try:
            from sic_browser import SICBrowser
            
            browser = SICBrowser(headless=True)
            try:
                print(f"\nBuscando documentos con Selenium para: '{args.terminos}'")
                resultados = browser.buscar_documentos(args.terminos)
                
                if not resultados:
                    print("No se encontraron resultados con Selenium.")
                    return
                
                print(f"Se encontraron {len(resultados)} documentos.")
                
                # Limitar si es necesario
                if args.max:
                    resultados = resultados[:args.max]
                
                # Guardar los resultados en JSON
                resultados_file = os.path.join(args.dir, "resultados.json")
                with open(resultados_file, 'w', encoding='utf-8') as f:
                    json.dump(resultados, f, indent=2, ensure_ascii=False)
                
                print(f"Resultados guardados en: {resultados_file}")
                
                # Procesar los resultados para descargar documentos
                for i, doc in enumerate(resultados, 1):
                    titulo = doc.get("titulo", "")
                    enlace = doc.get("enlace", "")
                    doc_id = doc.get("id", "")
                    
                    if not enlace:
                        print(f"[{i}/{len(resultados)}] Sin enlace para documento: {titulo}")
                        continue
                    
                    print(f"\n[{i}/{len(resultados)}] Procesando: {titulo}")
                    print(f"  URL: {enlace}")
                    
                    # Crear nombre base para el archivo
                    nombre_base = f"{i:02d}"
                    if doc_id:
                        nombre_base += f"_{doc_id}"
                    
                    # Intentar descargar
                    resultado = browser.obtener_documento(enlace, args.dir)
                    
                    if resultado:
                        print(f"  ✓ Documento descargado con éxito.")
                    else:
                        print(f"  × No se pudo descargar el documento.")
                    
                    # Esperar entre documentos
                    time.sleep(2)
                
            finally:
                browser.cerrar()
                
        except Exception as e:
            print(f"Error al usar Selenium: {e}")
            print("\n⚠ Ambos métodos de descarga fallaron. Consulte la documentación o contacte al desarrollador.")

if __name__ == "__main__":
    main()