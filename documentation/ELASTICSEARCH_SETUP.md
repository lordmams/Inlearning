# 🔍 Configuration Elasticsearch pour E-Learning

## 📋 Vue d'ensemble

Elasticsearch est maintenant intégré au système d'importation de cours pour fournir :
- **Recherche avancée** dans les cours
- **Indexation automatique** lors des imports
- **Suggestions d'autocomplétion**
- **Analytics de recherche**

## 🛠️ Configuration

### 1. Variables d'Environnement

Créez un fichier `.env` à la racine du projet :

```bash
# Copier le template
cp env.example .env
```

**Variables Elasticsearch importantes :**
```env
# Elasticsearch Configuration
ELASTICSEARCH_ENABLED=true
ELASTICSEARCH_HOST=elasticsearch:9200
ELASTICSEARCH_INDEX=courses
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=

# Autres configurations importantes
SECRET_KEY=your-secret-key-here-change-in-production
ANTHROPIC_API_KEY=your-anthropic-api-key-here
EMAIL_NOTIFICATIONS_ENABLED=false
ADMIN_NOTIFICATION_EMAILS=admin@example.com
```

### 2. Services Docker

Le `docker-compose.yaml` inclut maintenant :

```yaml
services:
  elasticsearch:    # Moteur de recherche (port 9200)
  kibana:          # Interface Elasticsearch (port 5601)
  redis:           # Cache (port 6379)
  app:             # Django avec Elasticsearch activé
  consumer:        # Consumer avec indexation automatique
```

## 🚀 Démarrage

### 1. Démarrer tous les services
```bash
docker-compose up -d
```

### 2. Vérifier Elasticsearch
```bash
# Santé du cluster
curl http://localhost:9200/_cluster/health

# Vérifier l'index
curl http://localhost:9200/courses/_search
```

### 3. Configurer l'index
```bash
# Entrer dans le container Django
docker-compose exec app bash

# Configurer Elasticsearch
python manage.py setup_elasticsearch --reindex
```

## 🔧 Commandes de Gestion

### Configuration initiale
```bash
# Créer l'index et indexer tous les cours
python manage.py setup_elasticsearch --reindex

# Recréer l'index complètement
python manage.py setup_elasticsearch --delete-index --reindex

# Juste vérifier la configuration
python manage.py setup_elasticsearch
```

### Réindexation
```bash
# Via l'interface admin
http://localhost:8080/admin-dashboard/elasticsearch/reindex/

# Via la commande
python manage.py setup_elasticsearch --reindex
```

## 🔍 Utilisation

### 1. Indexation Automatique

Les cours sont automatiquement indexés lors :
- **Import manuel** via l'interface admin
- **Import automatique** via le consumer
- **Création/modification** de cours dans l'admin Django

### 2. Recherche dans l'Interface

L'interface admin inclut maintenant :
- **Recherche avancée** dans les cours
- **Filtres par catégorie/difficulté**
- **Suggestions d'autocomplétion**

### 3. API de Recherche

```python
from services.elastic_service import ElasticService

elastic = ElasticService()

# Recherche simple
results = elastic.search_courses("python programming")

# Recherche avec filtres
results = elastic.search_courses(
    query="django",
    filters={
        'category': 'Web Development',
        'difficulty': 'intermediate',
        'is_free': True
    }
)

# Suggestions
suggestions = elastic.get_suggestions("pyt")
```

## 📊 Monitoring

### 1. Elasticsearch Health
```bash
# Via API
curl http://localhost:9200/_cluster/health

# Via Django
http://localhost:8080/admin-dashboard/elasticsearch/status/
```

### 2. Kibana (Interface Web)
```
http://localhost:5601
```

**Fonctionnalités Kibana :**
- Exploration des données indexées
- Création de visualisations
- Monitoring des performances
- Analyse des requêtes

### 3. Statistiques dans Django
```
http://localhost:8080/admin-dashboard/pipeline/monitoring/
```

## 🎯 Fonctionnalités Avancées

### 1. Recherche Multi-Critères
```python
# Recherche dans titre, description, instructeur
results = elastic.search_courses(
    query="machine learning",
    filters={
        'min_price': 0,
        'max_price': 100,
        'learning_mode': 'video'
    }
)
```

### 2. Analytics
```python
# Obtenir des statistiques
analytics = elastic.get_analytics()
# Retourne: total_courses, categories, difficulties, etc.
```

### 3. Suggestions d'Autocomplétion
```python
# Suggestions basées sur le titre des cours
suggestions = elastic.get_suggestions("react")
# Retourne: ["React Fundamentals", "React Advanced", ...]
```

## 🐛 Dépannage

### ❌ Elasticsearch ne démarre pas
```bash
# Vérifier les logs
docker-compose logs elasticsearch

# Vérifier la mémoire (Elasticsearch nécessite au moins 1GB)
docker stats

# Augmenter la mémoire virtuelle (Linux)
sudo sysctl -w vm.max_map_count=262144
```

### 🔗 Connexion refusée
```bash
# Vérifier que le service est démarré
docker-compose ps

# Tester la connectivité depuis Django
docker-compose exec app curl elasticsearch:9200
```

### 📊 Index vide
```bash
# Vérifier si des cours existent
docker-compose exec app python manage.py shell
>>> from courses.models import Course
>>> Course.objects.count()

# Réindexer manuellement
docker-compose exec app python manage.py setup_elasticsearch --reindex
```

### 🔍 Recherche ne fonctionne pas
```bash
# Vérifier l'index
curl http://localhost:9200/courses/_search

# Vérifier les logs Django
docker-compose logs app | grep elasticsearch

# Tester l'API de recherche
curl -X POST http://localhost:8080/admin-dashboard/api/search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "python"}'
```

## ⚙️ Configuration Avancée

### 1. Authentification Elasticsearch
```env
# Dans .env
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your-password
```

### 2. Cluster Multi-Nœuds
```yaml
# docker-compose.yaml
elasticsearch:
  environment:
    - discovery.type=zen
    - cluster.initial_master_nodes=elasticsearch
```

### 3. Mapping Personnalisé
Modifiez `services/elastic_service.py` pour personnaliser le mapping :

```python
def _get_course_mapping(self):
    return {
        'properties': {
            'title': {
                'type': 'text',
                'analyzer': 'french',  # Analyseur français
                'fields': {'keyword': {'type': 'keyword'}}
            },
            # ... autres champs
        }
    }
```

## 📈 Performance

### 1. Optimisation des Requêtes
- Utiliser des filtres plutôt que des requêtes quand possible
- Limiter la taille des résultats (`size` parameter)
- Utiliser la pagination (`from_` parameter)

### 2. Monitoring
```bash
# Statistiques de performance
curl http://localhost:9200/_stats

# Informations sur les nœuds
curl http://localhost:9200/_nodes/stats
```

### 3. Maintenance
```bash
# Forcer un merge des segments
curl -X POST http://localhost:9200/courses/_forcemerge

# Nettoyer le cache
curl -X POST http://localhost:9200/_cache/clear
```

## 🔄 Workflow Complet

1. **Démarrage** → `docker-compose up -d`
2. **Configuration** → `python manage.py setup_elasticsearch --reindex`
3. **Import de cours** → Via interface ou consumer
4. **Indexation automatique** → ElasticService
5. **Recherche** → Interface admin ou API
6. **Monitoring** → Kibana + Django admin

---

**🔍 Elasticsearch intégré et prêt pour la recherche avancée !** 