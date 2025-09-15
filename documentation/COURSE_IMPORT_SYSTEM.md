# 🎓 Système d'Importation de Cours E-Learning

## 📋 Vue d'ensemble

Ce système permet d'importer des cours en temps réel via plusieurs méthodes :
- **Upload manuel** via l'interface admin
- **Drop de fichiers** dans le répertoire surveillé (`ingest/drop/`)
- **Pipeline automatisé** avec traitement, normalisation et indexation

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Interface     │    │    Consumer     │    │  Elasticsearch  │
│     Admin       │────│   (Watchdog)    │────│   Indexation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │   PostgreSQL    │              │
         └──────────────│   (Logs/Data)   │──────────────┘
                        └─────────────────┘
```

## 📁 Structure des Répertoires

```
ingest/
├── drop/          # Fichiers à traiter (surveillé)
├── processing/    # Fichiers en cours de traitement
├── processed/     # Fichiers traités avec succès
└── error/         # Fichiers en erreur
```

## 🚀 Fonctionnalités

### ✨ Interface Admin Enrichie

#### 🎛️ Dashboard d'Importation
- **Upload de fichiers** : CSV, JSON, Excel
- **Mode test** : Aperçu sans sauvegarde
- **Templates** : Génération automatique d'exemples
- **Historique** : Suivi des importations

#### 📊 Monitoring Pipeline
- **Statut temps réel** des répertoires
- **Logs détaillés** d'importation
- **Consumer health check**
- **Statistiques Elasticsearch**

#### 🔧 Actions en Lot
- Activation/désactivation de cours
- Export de données
- Duplication de cours
- Suppression groupée

### 🤖 Consumer Automatique

Le consumer surveille le répertoire `ingest/drop/` et traite automatiquement :

1. **Détection** : Fichiers déposés (watchdog)
2. **Validation** : Format, taille, structure
3. **Normalisation** : Nettoyage et standardisation
4. **Traitement** : Import/update en base
5. **Indexation** : Ajout à Elasticsearch
6. **Notification** : Emails/webhooks de résultat
7. **Archivage** : Déplacement vers processed/error

### 🔍 Services Intégrés

#### 📝 CourseImporter
```python
from services.course_importer import CourseImporter

importer = CourseImporter()
result = importer.import_from_file(
    file=uploaded_file,
    format_type='csv',  # csv, json, xlsx
    update_existing=True,
    dry_run=False
)
```

#### 🔧 CourseProcessor
- Normalisation des titres/descriptions
- Validation des difficultés/modes
- Traitement des leçons
- Génération de tags
- Score de qualité

#### 🔍 ElasticService
- Indexation automatique
- Recherche avancée
- Suggestions d'autocomplétion
- Analytics de recherche

#### 📧 NotificationService
- Emails de succès/erreur
- Webhooks (Slack, Discord, Teams)
- Résumés quotidiens
- Notifications consumer

## 📄 Formats Supportés

### 🗂️ CSV
```csv
title,description,category,instructor,duration,difficulty,learning_mode,price,is_free,lessons,tags
"Python Basics","Introduction au Python","Programmation","Jean Dupont",10,"beginner","text",0,true,"Intro;Variables;Functions","python,beginner"
```

### 📋 JSON
```json
[
  {
    "title": "Django Advanced",
    "description": "Concepts avancés Django",
    "category": "Web Development",
    "instructor": "Marie Martin",
    "duration": 20,
    "difficulty": "advanced",
    "learning_mode": "practice",
    "price": 99.99,
    "is_free": false,
    "lessons": [
      {
        "title": "Models avancés",
        "content": "Relations complexes...",
        "order": 1,
        "video_url": "https://example.com/video1"
      }
    ],
    "tags": ["django", "python", "advanced"]
  }
]
```

### 📊 Excel
- Même structure que CSV
- Support des formules
- Onglets multiples (premier utilisé)

## 🛠️ Installation et Configuration

### 1. Dépendances
```bash
pip install watchdog elasticsearch-py pandas openpyxl requests
```

### 2. Configuration Django
```python
# settings.py
ELASTICSEARCH_ENABLED = True
ELASTICSEARCH_HOST = 'localhost:9200'
ELASTICSEARCH_INDEX = 'courses'

EMAIL_NOTIFICATIONS_ENABLED = True
ADMIN_NOTIFICATION_EMAILS = ['admin@example.com']

NOTIFICATION_WEBHOOKS = {
    'slack': 'https://hooks.slack.com/...',
    'discord': 'https://discord.com/api/webhooks/...'
}
```

### 3. Migrations
```bash
python manage.py makemigrations courses
python manage.py migrate
```

### 4. Démarrage
```bash
# Application Django
python manage.py runserver

# Consumer (terminal séparé)
python start_consumer.py

# Ou avec Docker
docker-compose -f infra/docker-compose.yml up
```

## 🐳 Déploiement Docker

### Services Inclus
- **PostgreSQL** : Base de données principale
- **Elasticsearch** : Moteur de recherche
- **Redis** : Cache et sessions
- **Django** : Application web
- **Consumer** : Traitement de fichiers
- **Nginx** : Reverse proxy
- **Kibana** : Interface Elasticsearch
- **Prometheus/Grafana** : Monitoring

### Volumes Montés
```yaml
volumes:
  - ingest_drop:/app/ingest/drop
  - ingest_processing:/app/ingest/processing
  - ingest_processed:/app/ingest/processed
  - ingest_error:/app/ingest/error
```

## 📈 Monitoring et Analytics

### 🎯 Métriques Disponibles
- Nombre de fichiers traités
- Taux de succès/erreur
- Temps de traitement moyen
- Cours indexés dans Elasticsearch
- Statut du consumer

### 📊 Dashboards
- **Admin Django** : `/admin-dashboard/`
- **Pipeline Monitoring** : `/admin-dashboard/pipeline/monitoring/`
- **Kibana** : `http://localhost:5601` (Docker)
- **Grafana** : `http://localhost:3000` (Docker)

### 🚨 Alertes
- Erreurs d'importation (email immédiat)
- Consumer arrêté (webhook)
- Résumé quotidien (email planifié)

## 🔧 API et Intégrations

### REST Endpoints
```
GET  /admin-dashboard/pipeline/consumer/status/  # Statut consumer
GET  /admin-dashboard/elasticsearch/status/      # Statut Elasticsearch
POST /admin-dashboard/courses/import/            # Import manuel
POST /admin-dashboard/elasticsearch/reindex/     # Réindexation
```

### Intégrations Externes
- **Slack** : Notifications temps réel
- **Discord** : Alertes d'équipe
- **Microsoft Teams** : Notifications entreprise
- **Email SMTP** : Rapports détaillés

## 🔐 Sécurité

### Authentification
- Décorateur `@staff_member_required`
- Permissions Django intégrées
- Sessions sécurisées

### Validation
- Taille de fichier limitée (10MB)
- Extensions autorisées
- Validation de contenu
- Sanitisation des données

### Logs et Audit
- Traçabilité complète des importations
- Logs détaillés dans PostgreSQL
- Archivage automatique des fichiers
- Monitoring des accès

## 🧪 Tests et Développement

### Tests Unitaires
```bash
python manage.py test services.tests
```

### Mode Debug
```python
# settings.py
DEBUG = True
ELASTICSEARCH_ENABLED = False  # Désactiver pour les tests
```

### Données de Test
```bash
# Générer des fichiers d'exemple
curl -X POST http://localhost:8000/admin-dashboard/courses/template/ \
  -d "template_type=bulk&format_type=json"
```

## 📚 Exemples d'Usage

### 1. Import Manuel
1. Aller sur `/admin-dashboard/courses/import/`
2. Choisir un fichier CSV/JSON
3. Sélectionner les options
4. Cliquer "Importer"

### 2. Import Automatique
```bash
# Copier un fichier dans le répertoire surveillé
cp courses.json ingest/drop/
# Le consumer traite automatiquement
```

### 3. Monitoring
```bash
# Vérifier le statut
curl http://localhost:8000/admin-dashboard/pipeline/consumer/status/
```

## 🐛 Dépannage

### Problèmes Courants

#### Consumer ne démarre pas
```bash
# Vérifier les logs
tail -f consumer.log

# Vérifier les permissions
ls -la ingest/
```

#### Elasticsearch inaccessible
```bash
# Tester la connexion
curl http://localhost:9200/_cluster/health
```

#### Fichiers bloqués en processing
```bash
# Déplacer manuellement
mv ingest/processing/* ingest/drop/
```

### Logs Utiles
- `consumer.log` : Logs du consumer
- Django admin : Logs d'importation
- Elasticsearch : `/var/log/elasticsearch/`
- PostgreSQL : Logs de requêtes

## 🚀 Prochaines Améliorations

- [ ] Support d'autres formats (XML, YAML)
- [ ] Import depuis URLs distantes
- [ ] Validation avancée avec schémas
- [ ] Interface de mapping personnalisé
- [ ] Intégration avec systèmes LMS externes
- [ ] API GraphQL pour les imports
- [ ] Machine Learning pour l'auto-catégorisation

---

**🎓 Système d'importation de cours - Prêt pour la production !** 