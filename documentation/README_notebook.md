# 📊 Notebook d'Analyse - Bloc 2

## 🎯 Objectif

Ce notebook Jupyter analyse les données du Bloc 2 du projet InLearning en intégrant les compétences et objectifs du **Référentiel Expert Science des Données YNOV 2024**.

## 📋 Contenu du Notebook

### 1. **Analyse Démographique des Étudiants**
- Distribution par âge et genre
- Profils types d'apprenants
- Segmentation par tranches d'âge

### 2. **Analyse des Langages et Technologies**
- Top 15 des langages préférés
- Alignement avec le référentiel 2024
- Gaps technologiques identifiés

### 3. **Analyse des Centres d'Intérêt**
- Top 20 des domaines d'intérêt
- Mapping avec les compétences du référentiel
- Tendances par segment d'utilisateurs

### 4. **Analyse des Niveaux Académiques**
- Distribution des diplômes
- Corrélation âge/expérience
- Profils de reconversion

### 5. **Analyse des Cours Disponibles**
- Distribution des niveaux de difficulté
- Top 15 des catégories
- Répartition gratuit vs payant

### 6. **Analyse de l'Adéquation Offre/Demande**
- Comparaison langages étudiants vs cours
- Identification des gaps
- Recommandations d'amélioration

### 7. **Recommandations Stratégiques**
- Couverture des compétences du référentiel 2024
- Priorités de développement
- Roadmap d'amélioration

## 🚀 Lancement du Notebook

### Méthode 1 : Script automatique
```bash
./lancer_notebook.sh
```

### Méthode 2 : Manuel
```bash
# Créer l'environnement virtuel
python3 -m venv venv_notebook

# Activer l'environnement
source venv_notebook/bin/activate

# Installer les dépendances
pip install -r requirements_notebook.txt

# Lancer Jupyter
jupyter notebook analyse_bloc2.ipynb
```

## 📊 Compétences du Référentiel 2024 Analysées

### **Data Engineering**
- Python, SQL, Apache Spark, Kafka, Airflow
- Pipeline de données, ETL, Data Warehousing

### **Data Analysis**
- Python, R, Pandas, NumPy, Matplotlib
- Analyse exploratoire, statistiques

### **Machine Learning**
- Python, Scikit-learn, TensorFlow, PyTorch
- Modèles prédictifs, apprentissage automatique

### **Big Data**
- Hadoop, Spark, Kafka, Elasticsearch
- Traitement de données massives

### **Cloud Computing**
- AWS, Azure, GCP, Docker, Kubernetes
- Déploiement et scalabilité

### **Data Visualization**
- Tableau, Power BI, D3.js, Plotly
- Communication des insights

### **Business Intelligence**
- SQL, Power BI, Tableau, Looker
- Aide à la décision

## 📈 Insights Attendus

1. **Profil Typique de l'Apprenant**
   - Âge, background, objectifs
   - Préférences d'apprentissage

2. **Gaps dans l'Offre de Formation**
   - Technologies manquantes
   - Niveaux de difficulté sous-représentés

3. **Opportunités de Développement**
   - Nouvelles catégories de cours
   - Parcours spécialisés

4. **Optimisation de la Recommandation**
   - Algorithme personnalisé
   - Segmentation des utilisateurs

## 🔧 Dépendances

- **pandas** : Manipulation des données
- **numpy** : Calculs numériques
- **matplotlib** : Visualisations
- **seaborn** : Graphiques statistiques
- **jupyter** : Interface notebook

## 📝 Notes

- Le notebook charge automatiquement les données depuis `LLM/generated_student_data.csv` et `Model/merged_courses_cleaned.json`
- Toutes les visualisations sont sauvegardées automatiquement
- Les recommandations sont basées sur l'analyse quantitative des données

## 🎯 Utilisation

1. **Exécuter toutes les cellules** pour l'analyse complète
2. **Modifier les paramètres** selon vos besoins
3. **Exporter les résultats** en PDF ou HTML
4. **Partager les insights** avec l'équipe

---

*Développé pour le projet InLearning - Bloc 2 - Référentiel Expert Science des Données YNOV 2024* 