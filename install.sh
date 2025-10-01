#!/bin/bash

echo "Instalando extensión Nemo Etiquetas..."

# Crear directorios
mkdir -p ~/.local/share/nemo-python/extensions/nemo-etiquetas

# Copiar archivos (asumiendo que están en el mismo directorio)
cp __init__.py ~/.local/share/nemo-python/extensions/nemo-etiquetas/
cp nemo_etiquetas.py ~/.local/share/nemo-python/extensions/
cp gestor_etiquetas.py ~/.local/share/nemo-python/extensions/nemo-etiquetas/
cp dialogo_etiquetas.py ~/.local/share/nemo-python/extensions/nemo-etiquetas/

# Dar permisos
chmod +x ~/.local/share/nemo-python/extensions/nemo_etiquetas.py

echo "Instalación completada."
echo "Reinicia Nemo con: nemo -q && nemo"

