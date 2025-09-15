# 🧪 Tests - InLearning Platform

Ce dossier contient tous les scripts de test pour valider le bon fonctionnement des différents composants de la plateforme InLearning.

## 📁 Structure des tests

### 🔧 Tests d'infrastructure
- **`test_elasticsearch_connection.py`** - Tests de connexion et configuration Elasticsearch
- **`test_consumer_integration.py`** - Tests d'intégration du consumer de fichiers
- **`test_spark_api.py`** - Tests de l'API Flask (anciennement Spark)

### 🌊 Tests d'orchestration
- **`test_airflow_dags.py`** - Tests et validation des DAGs Airflow

## 🚀 Exécution des tests

### Tests individuels
```bash
# Test Elasticsearch
python tests/test_elasticsearch_connection.py

# Test Consumer
python tests/test_consumer_integration.py

# Test API Flask
python tests/test_spark_api.py

# Test DAGs Airflow
python tests/test_airflow_dags.py
```

### Tests complets
```bash
# Exécuter tous les tests
python -m pytest tests/ -v

# Avec rapport de couverture
python -m pytest tests/ --cov=. --cov-report=html
```

## 📋 Prérequis

- Docker Compose en cours d'exécution
- Variables d'environnement configurées
- Services Elasticsearch, PostgreSQL, Redis actifs

## 🔍 Types de tests

### Tests de connectivité
- Vérification des connexions aux bases de données
- Tests des APIs REST
- Validation des configurations réseau

### Tests d'intégration
- Pipeline de traitement des cours
- Consumer de fichiers
- Orchestration Airflow

### Tests de validation
- Validation des schémas de données
- Tests de transformation ETL
- Vérification de l'intégrité des données

---
*Tests mis à jour le 13 septembre 2025* 