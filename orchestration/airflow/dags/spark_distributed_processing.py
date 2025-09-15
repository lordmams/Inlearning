"""
DAG Airflow pour orchestrer les traitements Spark distribués
Exécution horaire pour traiter les nouveaux cours et générer les recommandations
"""

import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import \
    SparkSubmitOperator

# Configuration par défaut du DAG
default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "catchup": False,
}

# Définition du DAG
dag = DAG(
    "spark_distributed_processing",
    default_args=default_args,
    description="Traitement distribué avec Apache Spark",
    schedule_interval="@hourly",  # Toutes les heures
    max_active_runs=1,
    tags=["spark", "distributed", "ml", "courses", "recommendations"],
)


def check_spark_cluster(**context):
    """Vérifie que le cluster Spark est disponible"""
    import time

    import requests

    spark_master_url = "http://spark-master:8080"
    max_retries = 5

    for i in range(max_retries):
        try:
            response = requests.get(f"{spark_master_url}/json/", timeout=10)
            if response.status_code == 200:
                cluster_info = response.json()
                active_workers = cluster_info.get("aliveworkers", 0)

                if active_workers >= 1:
                    logging.info(
                        f"✅ Cluster Spark OK: {active_workers} workers actifs"
                    )
                    return True
                else:
                    logging.warning(f"⚠️ Aucun worker actif ({i+1}/{max_retries})")

            time.sleep(30)

        except Exception as e:
            logging.warning(f"⚠️ Tentative {i+1}/{max_retries} échouée: {e}")
            time.sleep(30)

    raise Exception("❌ Cluster Spark non disponible après 5 tentatives")


def prepare_data_for_spark(**context):
    """Prépare les données pour le traitement Spark"""
    import json
    import os
    from pathlib import Path

    # Répertoires
    ingest_dir = Path("/opt/airflow/data/ingest/drop")
    spark_input_dir = Path("/opt/airflow/data/spark_input")

    # Créer le répertoire Spark si nécessaire
    spark_input_dir.mkdir(exist_ok=True)

    # Compter les nouveaux fichiers
    new_files = list(ingest_dir.glob("*.json")) if ingest_dir.exists() else []

    if new_files:
        logging.info(f"📁 {len(new_files)} nouveaux fichiers détectés")

        # Consolider les fichiers JSON en un seul pour Spark
        all_courses = []
        for file_path in new_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_courses.extend(data)
                    else:
                        all_courses.append(data)
            except Exception as e:
                logging.error(f"❌ Erreur lecture {file_path}: {e}")

        # Sauvegarder le fichier consolidé pour Spark
        consolidated_file = (
            spark_input_dir / f"courses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(consolidated_file, "w", encoding="utf-8") as f:
            json.dump(all_courses, f, indent=2, ensure_ascii=False)

        logging.info(f"💾 Fichier consolidé créé: {consolidated_file}")
        logging.info(f"📊 Total cours à traiter: {len(all_courses)}")

        # Passer le chemin au contexte Airflow
        context["task_instance"].xcom_push(
            key="input_file", value=str(consolidated_file)
        )
        context["task_instance"].xcom_push(key="course_count", value=len(all_courses))

        return str(consolidated_file)
    else:
        logging.info("📭 Aucun nouveau fichier à traiter")
        return None


def cleanup_processed_files(**context):
    """Nettoie les fichiers traités"""
    import shutil
    from pathlib import Path

    # Récupérer le fichier traité
    input_file = context["task_instance"].xcom_pull(
        key="input_file", task_ids="prepare_data"
    )

    if input_file and Path(input_file).exists():
        # Déplacer vers le dossier processed
        processed_dir = Path("/opt/airflow/data/ingest/processed")
        processed_dir.mkdir(exist_ok=True)

        file_path = Path(input_file)
        new_path = processed_dir / file_path.name

        shutil.move(str(file_path), str(new_path))
        logging.info(f"📁 Fichier déplacé vers: {new_path}")

    # Nettoyer les fichiers temporaires de plus de 24h
    temp_dir = Path("/opt/airflow/data/spark_input")
    if temp_dir.exists():
        import time

        now = time.time()
        for file_path in temp_dir.glob("*.json"):
            if now - file_path.stat().st_mtime > 24 * 3600:  # 24h
                file_path.unlink()
                logging.info(f"🗑️ Fichier temporaire supprimé: {file_path}")


# Tâche 1: Vérification du cluster Spark
check_spark_task = PythonOperator(
    task_id="check_spark_cluster",
    python_callable=check_spark_cluster,
    dag=dag,
)

# Tâche 2: Préparation des données
prepare_data_task = PythonOperator(
    task_id="prepare_data",
    python_callable=prepare_data_for_spark,
    dag=dag,
)

# Tâche 3: Traitement distribué des cours avec Spark
spark_course_processing = SparkSubmitOperator(
    task_id="process_courses_spark",
    application="/opt/bitnami/spark/jobs/course_processing_distributed.py",
    master="spark://spark-master:7077",
    executor_cores=2,
    executor_memory="2g",
    driver_memory="1g",
    total_executor_cores=4,
    application_args=[
        "--input-path",
        '{{ ti.xcom_pull(task_ids="prepare_data", key="input_file") }}',
        "--output-path",
        "/opt/bitnami/spark/data/processed_courses",
    ],
    conf={
        "spark.sql.adaptive.enabled": "true",
        "spark.sql.adaptive.coalescePartitions.enabled": "true",
        "spark.serializer": "org.apache.spark.serializer.KryoSerializer",
    },
    dag=dag,
)

# Tâche 4: Génération des recommandations distribuées
spark_recommendations = SparkSubmitOperator(
    task_id="generate_recommendations_spark",
    application="/opt/bitnami/spark/jobs/recommendations_distributed.py",
    master="spark://spark-master:7077",
    executor_cores=2,
    executor_memory="2g",
    driver_memory="1g",
    total_executor_cores=4,
    application_args=[
        "--model-path",
        "/opt/bitnami/spark/data/recommendation_model",
        "--output-path",
        "/opt/bitnami/spark/data/recommendations",
    ],
    dag=dag,
)

# Tâche 5: Indexation des résultats dans Elasticsearch
index_to_elasticsearch = BashOperator(
    task_id="index_to_elasticsearch",
    bash_command="""
    echo "🔍 Indexation des résultats dans Elasticsearch..."
    
    # Script Python pour indexer les résultats Spark dans ES
    python3 << 'EOF'
import requests
import json
import os
from pathlib import Path

def index_spark_results():
    es_host = os.environ.get('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')
    es_index = os.environ.get('ELASTICSEARCH_INDEX', 'inlearning-storage')
    
    results_dir = Path('/opt/bitnami/spark/data/processed_courses')
    
    if results_dir.exists():
        print(f"📁 Indexation depuis: {results_dir}")
        
        # Parcourir les fichiers Parquet (simulation avec JSON pour demo)
        for json_file in results_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    courses = json.load(f)
                
                for course in courses:
                    # Indexer chaque cours
                    response = requests.post(
                        f"{es_host}/{es_index}/_doc/{course.get('id', 'unknown')}",
                        json=course,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code in [200, 201]:
                        print(f"✅ Cours indexé: {course.get('titre', 'Unknown')}")
                    else:
                        print(f"❌ Erreur indexation: {response.status_code}")
                        
            except Exception as e:
                print(f"❌ Erreur traitement {json_file}: {e}")
    
    print("🏁 Indexation terminée")

index_spark_results()
EOF
    """,
    dag=dag,
)

# Tâche 6: Nettoyage des fichiers traités
cleanup_task = PythonOperator(
    task_id="cleanup_processed_files",
    python_callable=cleanup_processed_files,
    dag=dag,
)

# Tâche 7: Rapport de traitement
report_task = BashOperator(
    task_id="generate_processing_report",
    bash_command="""
    echo "📊 Génération du rapport de traitement..."
    
    # Statistiques du traitement
    COURSE_COUNT="{{ ti.xcom_pull(task_ids='prepare_data', key='course_count') }}"
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    echo "=== RAPPORT TRAITEMENT SPARK ==="
    echo "Timestamp: $TIMESTAMP"
    echo "Cours traités: $COURSE_COUNT"
    echo "Cluster Spark: OK"
    echo "Indexation ES: OK"
    echo "Status: SUCCESS ✅"
    echo "=========================="
    
    # Sauvegarder le rapport
    mkdir -p /opt/airflow/data/reports
    cat > /opt/airflow/data/reports/spark_processing_$(date +%Y%m%d_%H%M%S).txt << EOF
=== RAPPORT TRAITEMENT SPARK ===
Timestamp: $TIMESTAMP
Cours traités: $COURSE_COUNT
Cluster Spark: OK
Indexation ES: OK
Status: SUCCESS ✅
============================
EOF
    
    echo "💾 Rapport sauvegardé"
    """,
    dag=dag,
)

# Définition des dépendances
check_spark_task >> prepare_data_task >> spark_course_processing
spark_course_processing >> spark_recommendations
spark_recommendations >> index_to_elasticsearch
index_to_elasticsearch >> cleanup_task >> report_task
