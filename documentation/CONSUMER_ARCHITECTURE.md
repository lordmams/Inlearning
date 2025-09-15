# 🔄 Architecture Consumer Unifiée

## 📋 Vue d'ensemble

Cette architecture unifie l'import de cours via un **consumer de fichiers** qui surveille automatiquement les dépôts et traite les données via le **Learning Platform API**.

## 🏗️ Architecture Finale

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│ Interface Django│ -> │ File System  │ -> │ Consumer        │ -> │ Learning     │
│ (Upload Web)    │    │ (/ingest)    │    │ (Surveillance)  │    │ Platform API │
└─────────────────┘    └──────────────┘    └─────────────────┘    └──────────────┘
                                                                           │
                                                                           ▼
                                                                  ┌──────────────┐
                                                                  │ Elasticsearch│
                                                                  │ (Index final)│
                                                                  └──────────────┘
```

## 🎯 Flux de données

### 1. **Upload via Interface Django**
- L'utilisateur upload un fichier JSON/CSV via l'interface web
- Django sauvegarde le fichier dans `/ingest/drop/`
- Django crée un fichier de métadonnées `.meta`

### 2. **Detection par Consumer**
- Le consumer surveille le dossier `/ingest/drop/`
- Détection automatique des nouveaux fichiers
- Déplacement vers `/ingest/processing/`

### 3. **Traitement des Données**
- Parsing du fichier (JSON/CSV/XLSX)
- Conversion au format attendu par l'API
- Validation des données

### 4. **Envoi au Learning Platform**
- Appel direct à l'API Learning Platform
- Endpoints: `/process-single-course` ou `/process-courses-batch`
- Enrichissement ML (catégories, niveaux, embeddings)

### 5. **Indexation Elasticsearch**
- Le Learning Platform indexe directement dans Elasticsearch
- Données enrichies et normalisées
- Vecteurs d'embedding inclus

## 📁 Structure des fichiers

### Dossiers de traitement
```
/ingest/
├── drop/          # Dépôt initial des fichiers
├── processing/    # Fichiers en cours de traitement
├── processed/     # Fichiers traités avec succès
└── error/         # Fichiers en erreur
```

### Format des métadonnées
```json
{
  "original_filename": "cours_python.json",
  "format_type": "json",
  "uploaded_by": "admin",
  "uploaded_at": "2024-01-15T10:30:00",
  "file_size": 2048
}
```

## 🔧 Configuration

### Variables d'environnement
```bash
# Learning Platform API
LEARNING_PLATFORM_URL=http://localhost:8000

# Consumer (optionnel)
DJANGO_API_URL=http://app:8000  # Pour les logs
API_TOKEN=your_token_here       # Pour l'authentification
```

### Django Settings
```python
# Configuration Consumer (Learning Platform)
LEARNING_PLATFORM_URL = os.environ.get('LEARNING_PLATFORM_URL', 'http://localhost:8000')
```

## 🚀 Utilisation

### 1. Interface Web Django
1. Aller sur `/admin-dashboard/elasticsearch/import/`
2. Sélectionner un fichier JSON/CSV
3. Choisir "Validation uniquement" pour tester
4. Ou cliquer "Déposer pour le Consumer" pour traiter

### 2. Dépôt direct de fichiers
```bash
# Copier un fichier dans le dossier drop
cp mon_cours.json /path/to/ingest/drop/

# Le consumer le détectera automatiquement
```

### 3. API directe
```bash
# Test direct de l'API Learning Platform
curl -X POST http://localhost:8000/process-single-course \
  -H "Content-Type: application/json" \
  -d @cours.json
```

## 📊 Formats supportés

### JSON (Recommandé)
```json
{
  "url": "https://exemple.com/cours",
  "cours": {
    "id": "cours_001",
    "titre": "Titre du cours",
    "description": "Description",
    "contenus": {
      "paragraphs": ["paragraphe 1"],
      "lists": [["item1", "item2"]],
      "examples": ["code exemple"]
    },
    "categories": ["cat1", "cat2"],
    "niveau": "Débutant"
  }
}
```

### CSV
```csv
titre,description,categories,niveau,url
"Introduction Python","Cours de base","Programmation,Python","Débutant","https://exemple.com"
```

## 🔍 Monitoring

### Logs du Consumer
```bash
# Logs en temps réel
tail -f learning_platform/logs/consumer.log
```

### Status du Learning Platform
```bash
# Health check
curl http://localhost:8000/health

# Statistiques
curl http://localhost:8000/stats/processed-courses
```

## 🧪 Tests

### Script de test automatique
```bash
python test_consumer_integration.py
```

### Test manuel
1. Déposer un fichier de test dans `/ingest/drop/`
2. Vérifier les logs du consumer
3. Vérifier que le fichier est déplacé vers `/processed/`
4. Vérifier l'indexation dans Elasticsearch

## ⚡ Avantages de cette architecture

### ✅ **Simplicité**
- Un seul flux de données unifié
- Moins de code à maintenir
- Architecture plus cohérente

### ✅ **Robustesse**
- File watching automatique
- Retry logic intégré
- Gestion d'erreurs centralisée

### ✅ **Flexibilité**
- Support multiple formats
- Traitement batch et unitaire
- Interface web ET dépôt direct

### ✅ **Performance**
- Traitement asynchrone
- Enrichissement ML automatique
- Indexation directe Elasticsearch

### ✅ **Monitoring**
- Logs centralisés
- Dossiers d'état clairs
- API de monitoring

## 🔧 Composants modifiés

### Django (`elearning/`)
- `admin_dashboard/views.py` - Simplifié pour dépôt de fichiers
- `templates/elasticsearch_import.html` - Interface adaptée
- `settings.py` - Configuration Learning Platform
- Suppression de `SparkPipelineService`

### Consumer (`learning_platform/services/course_consumer.py`)
- Ajout de `_send_to_learning_platform_api()`
- Ajout de `_parse_file_data()`
- Support CSV/XLSX via pandas
- Conversion automatique des formats

### Learning Platform API (`learning_platform/api/app.py`)
- Endpoints `/process-single-course` et `/process-courses-batch`
- Intégration ML pipeline
- Indexation Elasticsearch directe

## 🎯 Prochaines étapes

1. **Tests en production** - Valider avec de vrais fichiers
2. **Monitoring avancé** - Dashboard de surveillance
3. **Optimisations** - Performance et mémoire
4. **Documentation** - Guide utilisateur complet

---

*Architecture Consumer Unifiée - Version 1.0* 