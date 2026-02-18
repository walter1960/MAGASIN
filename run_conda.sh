#!/bin/bash
# Script de lancement utilisant l'environnement Conda existant (ProjectAnac)

# 1. Se placer dans le dossier du projet
cd "$(dirname "$0")/magasin-ia-vision"

# 2. Utiliser l'interpréteur Python de l'environnement Conda 'ProjectAnac'
# Ajuster le chemin si nécessaire
PYTHON_EXEC="/home/walter/anaconda3/envs/ProjectAnac/bin/python"

# 3. Lancer l'application
export PYTHONPATH=$PYTHONPATH:$(pwd)
$PYTHON_EXEC -m app.main
