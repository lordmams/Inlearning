#!/bin/bash

echo "🧹 Nettoyage et redémarrage complet d'InLearning..."

# 1. Créer .env si manquant
if [ ! -f .env ]; then
    echo "📝 Création du fichier .env..."
    cp env.example .env
    echo "✅ Fichier .env créé"
fi

# 2. Arrêter tous les services
echo "🛑 Arrêt de tous les services..."
docker-compose down --remove-orphans

# 3. Nettoyer les conteneurs orphelins et les images
echo "🧹 Nettoyage des conteneurs orphelins..."
docker system prune -f

# 4. Supprimer les images existantes pour forcer la reconstruction
echo "🗑️ Suppression des images existantes..."
docker rmi -f inlearning_app inlearning_flask_api inlearning_consumer 2>/dev/null || true

# 5. Reconstruction complète sans cache
echo "🔨 Reconstruction complète des images..."
docker-compose build --no-cache --parallel

# 6. Démarrage des services
echo "🚀 Démarrage des services..."
docker-compose up -d

# 7. Attendre le démarrage
echo "⏳ Attente du démarrage (30 secondes)..."
sleep 30

# 8. Vérifier le statut
echo "📊 Statut des services:"
docker-compose ps

# 9. Afficher les logs récents
echo "📝 Logs récents de chaque service:"
echo "--- Django ---"
docker-compose logs --tail=10 app

echo "--- Flask API ---"
docker-compose logs --tail=10 flask_api

echo "--- Consumer ---"
docker-compose logs --tail=10 consumer

echo "--- PostgreSQL ---"
docker-compose logs --tail=5 db

# 10. Test de connectivité
echo "🔗 Test de connectivité:"
echo "  • Django: curl -s http://localhost:8080 | head -1"
echo "  • Flask API: curl -s http://localhost:5000 | head -1"

echo ""
echo "✅ Redémarrage terminé!"
echo "🌐 Services disponibles:"
echo "   • Django: http://localhost:8080"
echo "   • Flask API: http://localhost:5000"
echo "   • PgAdmin: http://localhost:9090"
echo ""
echo "🔧 Commandes utiles:"
echo "   • Logs en temps réel: docker-compose logs -f"
echo "   • Entrer dans Django: docker-compose exec app bash"
echo "   • Migrations: docker-compose exec app python manage.py migrate" 