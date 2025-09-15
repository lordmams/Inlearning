
# 🎓 InLearning Platform

## 📖 Description du projet

Dans l'ère numérique actuelle, l'éducation subit une transformation rapide, passant d'un modèle traditionnel à une approche plus personnalisée et flexible. Le projet **InLearning** vise à exploiter le Big Data et l'intelligence artificielle pour créer une plateforme innovante qui améliore l'expérience d'apprentissage et les résultats scolaires.

## 🏗️ Architecture

### Services principaux
- **Django Application** - Interface web et administration
- **Flask API** - Pipeline ML et traitement des cours
- **Elasticsearch** - Moteur de recherche et analytics
- **PostgreSQL** - Base de données principale
- **Apache Airflow** - Orchestration des workflows
- **Consumer** - Traitement automatique des fichiers

### Technologies utilisées
- Python 3.9+, Django, Flask
- Elasticsearch, PostgreSQL, Redis
- Docker & Docker Compose
- Apache Airflow, Pandas
- Machine Learning (scikit-learn)

## 📁 Structure du projet

```
InLearning/
├── 📚 documentation/          # Guides et documentation technique
├── 🧪 tests/                  # Scripts de test et validation
├── 🐳 elearning/             # Application Django principale
├── 🔧 learning_platform/     # API Flask et services ML
├── 🌊 orchestration/         # DAGs Airflow et workflows
├── 📊 LLM/                   # Modèles et analyses ML
├── 🕷️ Webscraping/           # Scripts de collecte de données
├── 📈 Model/                 # Modèles de classification
├── 🔍 reco_cours/            # Système de recommandation
└── 🛠️ ETL_users/             # Pipeline ETL utilisateurs
```

## 🚀 Installation et lancement

### Prérequis
- Docker et Docker Compose
- Python 3.9+
- Git

### Installation complète
```bash
# 1. Cloner le dépôt
git clone <repository-url>
cd InLearning

# 2. Configurer l'environnement
cp env.example .env
# Éditer .env avec vos configurations

# 3. Lancer tous les services
export AIRFLOW_UID=$(id -u)
docker-compose up -d --build

# 4. Vérifier les services
docker ps
```

### Services disponibles
- **Django Admin**: http://localhost:8000
- **Airflow UI**: http://localhost:8082 (admin/admin)
- **Elasticsearch**: http://localhost:9200
- **PgAdmin**: http://localhost:8081

## 📋 Livrables

- ✅ **Plateforme web Django** avec interface d'administration
- ✅ **Pipeline ML complet** de classification et traitement des cours
- ✅ **Moteur de recherche Elasticsearch** avec recommandations
- ✅ **Orchestration Airflow** pour l'automatisation ETL
- ✅ **Consumer temps réel** pour le traitement de fichiers
- ✅ **Tests automatisés** et validation de l'intégrité
- ✅ **Documentation complète** d'installation et d'utilisation

## 📚 Documentation

Consultez le dossier [`documentation/`](./documentation/) pour :
- Guides d'installation détaillés
- Architecture et design patterns
- Rapports de succès et configurations

## 🧪 Tests

Le dossier [`tests/`](./tests/) contient :
- Tests de connectivité des services
- Tests d'intégration du pipeline
- Validation des DAGs Airflow
- Tests de l'API et du consumer

## Contribution

Les contributions sont les bienvenues ! Merci de suivre les étapes suivantes :

1. Forkez le dépôt.
2. Créez une branche pour vos modifications :
   ```bash
   git checkout -b nouvelle-fonctionnalite
   ```
3. Effectuez un pull request après vos modifications.

## Licence

Ce projet est sous licence [MIT](LICENSE).

