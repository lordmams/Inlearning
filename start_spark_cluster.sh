#!/bin/bash

# Script de démarrage du cluster Apache Spark pour InLearning
# Démarre les services Spark et valide leur fonctionnement

set -e

echo "🚀 === DÉMARRAGE CLUSTER APACHE SPARK ==="
echo ""

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SPARK_MASTER_UI="http://localhost:8090"
FLASK_API="http://localhost:5000"
MAX_RETRIES=12
RETRY_DELAY=10

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fonction pour vérifier si un service est accessible
check_service() {
    local url=$1
    local service_name=$2
    local max_attempts=${3:-$MAX_RETRIES}
    
    print_status "Vérification de $service_name..."
    
    for i in $(seq 1 $max_attempts); do
        if curl -s --connect-timeout 5 "$url" > /dev/null 2>&1; then
            print_success "$service_name est accessible ✅"
            return 0
        fi
        
        if [ $i -lt $max_attempts ]; then
            print_warning "Tentative $i/$max_attempts échouée, nouvelle tentative dans ${RETRY_DELAY}s..."
            sleep $RETRY_DELAY
        fi
    done
    
    print_error "$service_name non accessible après $max_attempts tentatives ❌"
    return 1
}

# Vérifier les prérequis
print_status "Vérification des prérequis..."

if ! command -v docker &> /dev/null; then
    print_error "Docker n'est pas installé"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose n'est pas installé"
    exit 1
fi

print_success "Prérequis OK"

# Vérifier si .env existe
if [ ! -f .env ]; then
    print_warning "Fichier .env non trouvé, copie depuis env.example..."
    cp env.example .env
    print_status "Veuillez vérifier et ajuster les variables dans .env"
fi

# Variables d'environnement pour Airflow
export AIRFLOW_UID=$(id -u)
print_status "AIRFLOW_UID configuré: $AIRFLOW_UID"

# Créer les répertoires nécessaires
print_status "Création des répertoires Spark..."
mkdir -p learning_platform/spark/jobs
mkdir -p learning_platform/data/{input,output,processed_courses}
mkdir -p orchestration/airflow/logs
print_success "Répertoires créés"

# Copier les jobs Spark
print_status "Copie des jobs Spark..."
if [ -f "learning_platform/spark/course_processing_distributed.py" ]; then
    cp learning_platform/spark/course_processing_distributed.py learning_platform/spark/jobs/
fi
if [ -f "learning_platform/spark/recommendations_distributed.py" ]; then
    cp learning_platform/spark/recommendations_distributed.py learning_platform/spark/jobs/
fi
print_success "Jobs Spark copiés"

# Démarrer les services
print_status "Démarrage des services Docker Compose..."
docker-compose up -d

print_status "Attente du démarrage des services..."
sleep 20

# Vérifier les services critiques
print_status "Vérification des services..."

# PostgreSQL principal
if check_service "http://localhost:5432" "PostgreSQL" 6; then
    print_success "PostgreSQL principal OK"
else
    print_warning "PostgreSQL principal non accessible"
fi

# Redis
if check_service "http://localhost:6379" "Redis" 6; then
    print_success "Redis OK"
else
    print_warning "Redis non accessible"
fi

# Elasticsearch
if check_service "http://localhost:9200" "Elasticsearch" 8; then
    print_success "Elasticsearch OK"
else
    print_warning "Elasticsearch non accessible"
fi

# Flask API
if check_service "$FLASK_API/health" "Flask API" 8; then
    print_success "Flask API OK"
    
    # Vérifier le statut Spark dans l'API
    print_status "Vérification du statut Spark..."
    spark_status=$(curl -s "$FLASK_API/status" | jq -r '.spark_cluster.status' 2>/dev/null || echo "unknown")
    
    if [ "$spark_status" = "available" ]; then
        print_success "Spark intégré dans l'API ✅"
    else
        print_warning "Spark non intégré dans l'API (statut: $spark_status)"
    fi
else
    print_error "Flask API non accessible"
fi

# Spark Master UI
if check_service "$SPARK_MASTER_UI/json/" "Spark Master UI" 10; then
    print_success "Spark Master UI OK"
    
    # Récupérer les informations du cluster
    cluster_info=$(curl -s "$SPARK_MASTER_UI/json/" 2>/dev/null)
    if [ $? -eq 0 ]; then
        workers=$(echo "$cluster_info" | jq -r '.aliveworkers // 0' 2>/dev/null || echo "0")
        cores=$(echo "$cluster_info" | jq -r '.cores // 0' 2>/dev/null || echo "0")
        memory=$(echo "$cluster_info" | jq -r '.memory // 0' 2>/dev/null || echo "0")
        
        print_success "Cluster Spark configuré:"
        echo "  📊 Workers actifs: $workers"
        echo "  🖥️ Cores totaux: $cores"
        echo "  💾 Mémoire totale: ${memory} MB"
        
        if [ "$workers" -ge 2 ]; then
            print_success "Cluster Spark opérationnel avec $workers workers ✅"
        else
            print_warning "Cluster Spark avec seulement $workers worker(s)"
        fi
    fi
else
    print_error "Spark Master UI non accessible"
fi

# Airflow (si démarré en standalone)
if docker ps | grep -q "airflow-standalone"; then
    if check_service "http://localhost:8082" "Airflow UI" 6; then
        print_success "Airflow UI OK"
    else
        print_warning "Airflow UI non accessible"
    fi
fi

# Django Admin
if check_service "http://localhost:8000" "Django Admin" 6; then
    print_success "Django Admin OK"
else
    print_warning "Django Admin non accessible"
fi

echo ""
print_status "=== STATUT FINAL ==="

# Vérifier les containers
print_status "Containers Docker:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(spark|flask|django)"

echo ""
print_status "=== SERVICES DISPONIBLES ==="
echo "🌐 Django Admin:     http://localhost:8000"
echo "🔥 Flask API:        http://localhost:5000"
echo "⚡ Spark Master UI:  http://localhost:8090"
echo "🌊 Airflow UI:       http://localhost:8082"
echo "🔍 Elasticsearch:    http://localhost:9200"
echo "🐘 PgAdmin:          http://localhost:8081"

echo ""
print_status "=== TESTS DE VALIDATION ==="
echo "Pour tester l'intégration Spark:"
echo "  python tests/test_spark_integration.py"
echo ""
echo "Pour tester un job Spark simple:"
echo "  curl -X POST http://localhost:5000/process-courses-distributed \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '[{\"id\":\"test\",\"titre\":\"Test Spark\",\"description\":\"Test\"}]'"

echo ""
if docker ps | grep -q "spark-master.*Up" && docker ps | grep -q "spark-worker.*Up"; then
    print_success "🎉 CLUSTER SPARK DÉMARRÉ AVEC SUCCÈS!"
    echo ""
    echo "Le cluster Apache Spark est opérationnel avec calculs distribués."
    echo "Vous pouvez maintenant traiter des milliers de cours en parallèle!"
else
    print_error "⚠️ PROBLÈME AVEC LE CLUSTER SPARK"
    echo ""
    echo "Vérifiez les logs avec: docker-compose logs spark-master spark-worker-1"
fi 