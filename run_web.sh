#!/bin/bash
# Script de lancement de l'application web (FastAPI + PyWebView)

cd "$(dirname "$0")/magasin-ia-vision"

# Utiliser l'interpréteur Python de l'environnement Conda 'ProjectAnac'
PYTHON_EXEC="/home/walter/anaconda3/envs/ProjectAnac/bin/python"

# Lancer l'application desktop
export PYTHONPATH=$PYTHONPATH:$(pwd)
$PYTHON_EXEC desktop_app.py
