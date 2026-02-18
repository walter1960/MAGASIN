#!/bin/bash
# Script de lancement facile pour Linux

# 1. Se placer dans le dossier du projet
cd "$(dirname "$0")/magasin-ia-vision"

# 2. Activer l'environnement virtuel s'il existe (ajuster le chemin selon votre installation)
if [ -d "../venv" ]; then
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# 3. Lancer l'application
# Ajoute le dossier courant au PYTHONPATH pour éviter les erreurs d'import
export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 -m app.main
