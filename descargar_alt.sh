#!/bin/bash

# Verificar que se proporcionó un término de búsqueda
if [ -z "$1" ]; then
    echo "Uso: ./descargar_alt.sh 'términos de búsqueda' [--max N]"
    echo "Ejemplo: ./descargar_alt.sh 'derecho de retracto aerolineas'"
    exit 1
fi

# Construir el comando
CMD="python sic_alt_downloader.py \"$1\""

# Agregar opciones adicionales si se proporcionan
shift
if [ ! -z "$@" ]; then
    CMD="$CMD $@"
fi

# Mostrar el comando que se ejecutará
echo "Ejecutando: $CMD"
echo "-----------------------------------"

# Ejecutar el comando
eval $CMD
