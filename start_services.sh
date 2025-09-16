#!/bin/bash

echo "🚀 Démarrage des services InLearning..."

# Vérifier que .env existe
if [ ! -f .env ]; then
    echo "⚠️ Fichier .env manquant, création depuis le template..."
    cp env.example .env
    echo "✅ Fichier .env créé"
    echo "🔧 Veuillez configurer vos variables dans .env avant de continuer"
    exit 1
fi

# Arrêter les services existants
echo "🛑 Arrêt des services existants..."
docker-compose down

# Reconstruire les images
echo "🔨 Reconstruction des images..."
docker-compose build --no-cache

# Démarrer les services
echo "🚀 Démarrage des services..."
docker-compose up -d

# Attendre que les services soient prêts
echo "⏳ Attente du démarrage des services..."
sleep 15

# Vérifier le statut
echo "📊 Statut des services:"
docker-compose ps

# Afficher les logs en cas d'erreur
echo "📝 Logs récents:"
docker-compose logs --tail=20

echo "✅ Services démarrés!"
echo "🌐 Accès aux services:"
echo "   • Django Admin: http://localhost:8080/admin/"
echo "   • Flask API: http://localhost:5000/"
echo "   • PgAdmin: http://localhost:9090/"
echo "   • Redis: localhost:6379"
echo ""
echo "📁 Pour déposer des fichiers à traiter:"
echo "   docker-compose exec consumer ls /app/ingest/drop/" 