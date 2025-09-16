# 🚁 **Installation et Configuration d'Apache Airflow**

## 📋 **Vue d'ensemble**

Apache Airflow a été intégré dans le système InLearning pour orchestrer:
- **ETL quotidien** des utilisateurs (Excel → PostgreSQL)
- **Réindexation hebdomadaire** d'Elasticsearch avec snapshots

## 🏗️ **Architecture des DAGs**

### 1. **ETL Users Daily** (`etl_users_daily.py`)
- **Schedule**: Quotidien à 02:00 AM
- **Flow**: Excel → Transform → PostgreSQL
- **Fonctionnalités**:
  - Extraction depuis `/ETL_users/data.xlsx`
  - Transformation et validation des données
  - Chargement vers PostgreSQL avec gestion des conflits
  - Validation et rapport de qualité

### 2. **Reindex Weekly** (`reindex_weekly.py`)
- **Schedule**: Hebdomadaire le dimanche à 01:00 AM
- **Flow**: Snapshot → Reindex → Validate → Cleanup
- **Fonctionnalités**:
  - Snapshot pré-réindexation
  - Réindexation complète d'Elasticsearch
  - Validation de l'intégrité des données
  - Nettoyage des anciens indices (garde les 3 derniers)

## 🚀 **Installation**

### Option 1: Airflow Standalone (Recommandé pour développement)

```bash
# 1. Construction de l'image personnalisée
cd orchestration/airflow
docker build -t airflow-custom .

# 2. Lancement en mode standalone
docker run -d \
  --name airflow-standalone \
  --network inlearning_default \
  -p 8082:8080 \
  -v $(pwd)/orchestration/airflow/dags:/opt/airflow/dags \
  -v $(pwd)/orchestration/airflow/logs:/opt/airflow/logs \
  -v $(pwd)/ETL_users:/opt/airflow/data/ETL_users \
  -v $(pwd)/ingest:/opt/airflow/data/ingest \
  -e AIRFLOW__CORE__EXECUTOR=SequentialExecutor \
  -e AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=sqlite:////opt/airflow/airflow.db \
  -e AIRFLOW__CORE__FERNET_KEY='UKMzEm3yIuFYEq1y5siPHPjpO7yI-wV1hjaKRyb3S8c=' \
  -e AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=true \
  -e AIRFLOW__CORE__LOAD_EXAMPLES=false \
  -e ELASTICSEARCH_HOST=${ELASTICSEARCH_HOST} \
  -e ELASTICSEARCH_INDEX=${ELASTICSEARCH_INDEX} \
  -e LEARNING_PLATFORM_URL=http://flask_api:5000 \
  airflow-custom \
  bash -c "airflow db init && \
           airflow users create --username admin --firstname Admin --lastname User --role Admin --email admin@airflow.com --password admin && \
           airflow standalone"
```

### Option 2: Installation locale

```bash
# 1. Installation d'Airflow
pip install apache-airflow==2.7.1
pip install apache-airflow-providers-postgres==5.7.1

# 2. Configuration
export AIRFLOW_HOME=$(pwd)/orchestration/airflow
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/orchestration/airflow/dags

# 3. Initialisation
airflow db init
airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@airflow.com

# 4. Lancement
airflow standalone
```

## 🌐 **Accès Web UI**

- **URL**: http://localhost:8082
- **Username**: admin
- **Password**: admin

## 📊 **Monitoring et Logs**

### Logs des DAGs
```bash
# Logs par DAG
docker exec airflow-standalone ls -la /opt/airflow/logs/dag_id=etl_users_daily/
docker exec airflow-standalone ls -la /opt/airflow/logs/dag_id=reindex_weekly/

# Logs en temps réel
docker logs -f airflow-standalone
```

### Status des tâches
```bash
# Via CLI
docker exec airflow-standalone airflow dags state etl_users_daily 2025-01-13
docker exec airflow-standalone airflow tasks state etl_users_daily extract_users 2025-01-13
```

## 🔧 **Configuration des connexions**

### PostgreSQL Connection
```bash
docker exec airflow-standalone airflow connections add 'postgres_default' \
  --conn-type 'postgres' \
  --conn-host 'db' \
  --conn-schema 'elearning_db' \
  --conn-login 'elearning_user' \
  --conn-password 'elearning_password' \
  --conn-port 5432
```

## 📈 **Métriques et KPIs**

### ETL Users Daily
- **Taux de réussite**: > 95%
- **Qualité des données**: > 80% de lignes valides
- **Temps d'exécution**: < 10 minutes
- **Détection de doublons**: Basée sur email

### Reindex Weekly
- **Intégrité des données**: < 1% de perte acceptable
- **Temps de réindexation**: Varie selon la taille
- **Snapshots**: Conservation des 3 derniers
- **Nettoyage**: Automatique des anciens indices

## 🚨 **Alertes et Notifications**

### Configuration des notifications
```python
# Dans airflow.cfg ou via env vars
email_backend = 'airflow.providers.smtp.operators.email.EmailOperator'
smtp_host = 'localhost'
smtp_starttls = True
smtp_ssl = False
smtp_port = 587
smtp_mail_from = 'airflow@inlearning.com'
```

### Alertes configurées
- **DAG Failure**: Email + Log
- **Task Retry**: Log uniquement
- **SLA Miss**: Email + Dashboard

## 📝 **Maintenance**

### Nettoyage régulier
```bash
# Nettoyage des logs (> 30 jours)
docker exec airflow-standalone find /opt/airflow/logs -name "*.log" -mtime +30 -delete

# Nettoyage de la base de données
docker exec airflow-standalone airflow db clean --days 30
```

### Backup des DAGs
```bash
# Backup automatique
tar -czf airflow-dags-$(date +%Y%m%d).tar.gz orchestration/airflow/dags/
```

## 🔍 **Troubleshooting**

### Problèmes courants

1. **DAG non visible**
   ```bash
   # Vérifier les erreurs de parsing
   docker exec airflow-standalone airflow dags list-import-errors
   ```

2. **Connexion PostgreSQL échouée**
   ```bash
   # Tester la connexion
   docker exec airflow-standalone airflow connections test postgres_default
   ```

3. **Permissions de fichiers**
   ```bash
   # Ajuster les permissions
   sudo chown -R $(id -u):$(id -g) orchestration/airflow/
   ```

## 🎯 **Prochaines étapes**

1. **Monitoring avancé** avec Prometheus/Grafana
2. **Notifications Slack/Teams**
3. **DAGs pour ML Pipeline**
4. **Backup automatisé** des configurations
5. **Tests d'intégration** avec pytest

## 📚 **Ressources**

- [Documentation Airflow](https://airflow.apache.org/docs/)
- [Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [Provider Packages](https://airflow.apache.org/docs/apache-airflow-providers/) 