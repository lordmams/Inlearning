#!/bin/bash
set -e

# Script d'entrée pour learning_platform
# Permet de démarrer soit l'API Flask soit le Consumer

echo "🚀 Démarrage du service learning_platform..."
echo "📁 Répertoire de travail: $(pwd)"
echo "📋 Commande: $@"

# Si aucune commande spécifiée, démarrer l'API par défaut
if [ $# -eq 0 ]; then
    echo "🌐 Démarrage de l'API Flask..."
    cd /app/api
    exec python app.py
fi

# Si la commande contient "start_consumer.py", démarrer depuis /app
if [[ "$*" == *"start_consumer.py"* ]]; then
    echo "🤖 Démarrage du Consumer..."
    cd /app
    exec python start_consumer.py
fi

# Si la commande contient "app.py", démarrer depuis /app/api
if [[ "$*" == *"app.py"* ]]; then
    echo "🌐 Démarrage de l'API Flask..."
    cd /app/api
    exec python app.py
fi

# Sinon, exécuter la commande telle quelle
echo "⚙️ Exécution de la commande: $@"
exec "$@" 