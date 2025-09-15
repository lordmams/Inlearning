# 🚀 Proposition d'Intégration Apache Spark

## 🎯 Objectif
Intégrer Apache Spark au projet InLearning pour permettre les calculs distribués et améliorer les performances de traitement des gros volumes de données.

## 🏗️ Architecture Proposée

### Services additionnels
```yaml
# Ajout au docker-compose.yaml
spark-master:
  image: bitnami/spark:3.5
  environment:
    - SPARK_MODE=master
    - SPARK_RPC_AUTHENTICATION_ENABLED=no
    - SPARK_RPC_ENCRYPTION_ENABLED=no
  ports:
    - "8080:8080"  # Spark UI
    - "7077:7077"  # Spark Master

spark-worker-1:
  image: bitnami/spark:3.5
  environment:
    - SPARK_MODE=worker
    - SPARK_MASTER_URL=spark://spark-master:7077
    - SPARK_WORKER_MEMORY=2g
    - SPARK_WORKER_CORES=2
  depends_on:
    - spark-master

spark-worker-2:
  image: bitnami/spark:3.5
  environment:
    - SPARK_MODE=worker
    - SPARK_MASTER_URL=spark://spark-master:7077
    - SPARK_WORKER_MEMORY=2g
    - SPARK_WORKER_CORES=2
  depends_on:
    - spark-master
```

## 🔧 Cas d'usage pour Spark

### 1. **Traitement massif de cours**
```python
# learning_platform/spark/course_processing_distributed.py
from pyspark.sql import SparkSession
from pyspark.ml.feature import TfidfVectorizer
from pyspark.ml.classification import LogisticRegression

def process_courses_distributed(courses_path):
    spark = SparkSession.builder \
        .appName("CourseProcessing") \
        .master("spark://spark-master:7077") \
        .getOrCreate()
    
    # Charger les cours
    df = spark.read.json(courses_path)
    
    # Feature engineering distribué
    vectorizer = TfidfVectorizer(inputCol="content", outputCol="features")
    
    # Classification ML distribuée
    classifier = LogisticRegression(featuresCol="features", labelCol="category")
    
    # Pipeline distribué
    pipeline = Pipeline(stages=[vectorizer, classifier])
    model = pipeline.fit(df)
    
    return model.transform(df)
```

### 2. **Analytics en temps réel**
```python
# Spark Streaming pour le consumer
from pyspark.streaming import StreamingContext
from pyspark.sql.functions import *

def real_time_course_analytics():
    spark = SparkSession.builder \
        .appName("CourseStreamAnalytics") \
        .getOrCreate()
    
    # Stream depuis Kafka ou file system
    stream_df = spark \
        .readStream \
        .format("json") \
        .option("path", "/ingest/drop") \
        .load()
    
    # Agrégations en temps réel
    analytics = stream_df \
        .groupBy("category", window(col("timestamp"), "1 hour")) \
        .agg(
            count("*").alias("course_count"),
            avg("difficulty_score").alias("avg_difficulty")
        )
    
    # Output vers Elasticsearch
    query = analytics.writeStream \
        .outputMode("append") \
        .format("es") \
        .option("es.nodes", "elasticsearch:9200") \
        .start()
    
    return query
```

### 3. **Recommandations distribuées**
```python
# Système de recommandation avec MLlib
from pyspark.ml.recommendation import ALS

def distributed_course_recommendations():
    spark = SparkSession.builder \
        .appName("CourseRecommendations") \
        .getOrCreate()
    
    # Matrice utilisateur-cours
    interactions_df = spark.read.parquet("/data/user_course_interactions")
    
    # ALS (Alternating Least Squares) distribué
    als = ALS(
        maxIter=10,
        regParam=0.1,
        userCol="user_id",
        itemCol="course_id",
        ratingCol="rating"
    )
    
    model = als.fit(interactions_df)
    
    # Recommandations pour tous les utilisateurs
    recommendations = model.recommendForAllUsers(10)
    
    return recommendations
```

## 🌊 Intégration avec Airflow

### DAG Spark distribué
```python
# orchestration/airflow/dags/spark_distributed_processing.py
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

dag = DAG(
    'spark_distributed_processing',
    description='Traitement distribué avec Spark',
    schedule_interval='@hourly'
)

# Tâche Spark pour traitement massif
spark_course_processing = SparkSubmitOperator(
    task_id='process_courses_spark',
    application='/opt/airflow/spark/course_processing_distributed.py',
    master='spark://spark-master:7077',
    executor_cores=2,
    executor_memory='2g',
    dag=dag
)

# Tâche Spark pour recommandations
spark_recommendations = SparkSubmitOperator(
    task_id='generate_recommendations',
    application='/opt/airflow/spark/recommendations_distributed.py',
    master='spark://spark-master:7077',
    dag=dag
)

spark_course_processing >> spark_recommendations
```

## 📈 Avantages attendus

### Performance
- **Traitement parallèle** de milliers de cours simultanément
- **Scalabilité horizontale** (ajout de workers)
- **Optimisations automatiques** des requêtes

### Capabilities
- **Machine Learning distribué** avec MLlib
- **Streaming en temps réel** avec Spark Streaming
- **Analytics complexes** sur gros volumes

### Monitoring
- **Spark UI** pour monitoring des jobs
- **Métriques détaillées** de performance
- **Intégration** avec les logs Airflow

## 🛠️ Plan d'implémentation

### Phase 1 - Setup
1. Ajouter services Spark au docker-compose
2. Créer module PySpark dans learning_platform/
3. Adapter le consumer pour utiliser Spark

### Phase 2 - Migration
1. Migrer le pipeline ML vers Spark MLlib
2. Implémenter Spark Streaming pour temps réel
3. Créer DAGs Airflow avec SparkSubmitOperator

### Phase 3 - Optimisation
1. Tuning des performances Spark
2. Monitoring avancé
3. Auto-scaling des workers

## 📊 Métriques de succès

- **Débit** : >10x plus de cours traités/heure
- **Latence** : Réduction du temps de traitement batch
- **Scalabilité** : Capacité à traiter 100k+ cours
- **Disponibilité** : Tolérance aux pannes avec cluster Spark

---
*Proposition technique pour InLearning Platform - Septembre 2025* 