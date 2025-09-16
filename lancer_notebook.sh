#!/bin/bash

echo "🚀 Lancement du Notebook d'Analyse - Bloc 2"
echo "=========================================="

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv_notebook" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv_notebook
fi

# Activer l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..."
source venv_notebook/bin/activate

# Installer les dépendances
echo "📚 Installation des dépendances..."
pip install -r requirements_notebook.txt

# Lancer Jupyter Notebook
echo "📊 Lancement de Jupyter Notebook..."
echo "🌐 Le notebook sera accessible à l'adresse : http://localhost:8888"
echo "🔑 Token d'accès : (voir dans le terminal)"
echo ""
echo "📝 Pour arrêter le serveur : Ctrl+C"
echo ""

jupyter notebook analyse_bloc2.ipynb 