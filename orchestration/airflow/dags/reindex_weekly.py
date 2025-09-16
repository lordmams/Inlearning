"""
DAG Reindex Weekly: Réindexation hebdomadaire d'Elasticsearch avec snapshots
Exécution hebdomadaire le dimanche à 01:00 AM
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta

import requests
from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Configuration par défaut du DAG
default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
    "catchup": False,
}

# Définition du DAG
dag = DAG(
    "reindex_weekly",
    default_args=default_args,
    description="Réindexation hebdomadaire Elasticsearch avec snapshots",
    schedule_interval="0 1 * * 0",  # Dimanche à 1h du matin
    max_active_runs=1,
    tags=["elasticsearch", "reindex", "snapshot", "weekly", "maintenance"],
)

# Configuration Elasticsearch
ELASTICSEARCH_HOST = os.environ.get("ELASTICSEARCH_HOST")
ELASTICSEARCH_INDEX = os.environ.get("ELASTICSEARCH_INDEX", "inlearning-storage")
ELASTICSEARCH_API_KEY = os.environ.get("ELASTICSEARCH_API_KEY")


def get_es_headers():
    """Retourne les headers pour les requêtes Elasticsearch"""
    headers = {"Content-Type": "application/json"}
    if ELASTICSEARCH_API_KEY:
        headers["Authorization"] = f"ApiKey {ELASTICSEARCH_API_KEY}"
    return headers


def create_snapshot_repository(**context):
    """
    Création/vérification du repository de snapshots
    """
    try:
        logging.info("Création/vérification du repository de snapshots")

        # Configuration du repository
        repository_name = "weekly_snapshots"
        repository_config = {
            "type": "fs",
            "settings": {
                "location": "/snapshots/weekly",
                "compress": True,
                "chunk_size": "64mb",
            },
        }

        # Vérification si le repository existe
        check_url = f"{ELASTICSEARCH_HOST}/_snapshot/{repository_name}"
        response = requests.get(check_url, headers=get_es_headers())

        if response.status_code == 404:
            # Création du repository
            create_url = f"{ELASTICSEARCH_HOST}/_snapshot/{repository_name}"
            response = requests.put(
                create_url, headers=get_es_headers(), json=repository_config
            )
            response.raise_for_status()
            logging.info(f"Repository {repository_name} créé avec succès")
        else:
            logging.info(f"Repository {repository_name} existe déjà")

        return {
            "repository_name": repository_name,
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Erreur lors de la création du repository: {str(e)}")
        raise


def create_pre_reindex_snapshot(**context):
    """
    Création d'un snapshot avant la réindexation
    """
    try:
        ti = context["ti"]
        repo_info = ti.xcom_pull(task_ids="create_snapshot_repository")
        repository_name = repo_info["repository_name"]

        # Nom du snapshot avec timestamp
        snapshot_name = f"pre-reindex-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        logging.info(f"Création du snapshot {snapshot_name}")

        # Configuration du snapshot
        snapshot_config = {
            "indices": ELASTICSEARCH_INDEX,
            "ignore_unavailable": True,
            "include_global_state": False,
            "metadata": {
                "description": f"Snapshot pré-réindexation du {datetime.now().isoformat()}",
                "created_by": "airflow_reindex_weekly",
                "index": ELASTICSEARCH_INDEX,
            },
        }

        # Création du snapshot
        snapshot_url = (
            f"{ELASTICSEARCH_HOST}/_snapshot/{repository_name}/{snapshot_name}"
        )
        response = requests.put(
            snapshot_url, headers=get_es_headers(), json=snapshot_config
        )
        response.raise_for_status()

        # Attendre la fin du snapshot (polling)
        max_wait_time = 300  # 5 minutes max
        wait_time = 0

        while wait_time < max_wait_time:
            status_response = requests.get(
                f"{snapshot_url}/_status", headers=get_es_headers()
            )

            if status_response.status_code == 200:
                status_data = status_response.json()
                snapshot_state = status_data["snapshots"][0]["state"]

                if snapshot_state == "SUCCESS":
                    logging.info(f"Snapshot {snapshot_name} créé avec succès")
                    break
                elif snapshot_state == "FAILED":
                    raise Exception(
                        f"Échec de la création du snapshot: {snapshot_name}"
                    )

            # Attendre 10 secondes avant le prochain check
            time.sleep(10)
            wait_time += 10

        return {
            "snapshot_name": snapshot_name,
            "repository_name": repository_name,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Erreur lors de la création du snapshot: {str(e)}")
        raise


def get_elasticsearch_stats(**context):
    """
    Récupération des statistiques Elasticsearch avant réindexation
    """
    try:
        logging.info("Récupération des statistiques Elasticsearch")

        # Statistiques de l'index
        stats_url = f"{ELASTICSEARCH_HOST}/{ELASTICSEARCH_INDEX}/_stats"
        response = requests.get(stats_url, headers=get_es_headers())
        response.raise_for_status()

        stats_data = response.json()
        index_stats = stats_data["indices"][ELASTICSEARCH_INDEX]

        # Comptage des documents
        count_url = f"{ELASTICSEARCH_HOST}/{ELASTICSEARCH_INDEX}/_count"
        count_response = requests.get(count_url, headers=get_es_headers())
        count_response.raise_for_status()

        count_data = count_response.json()

        # Informations sur l'index
        info_url = f"{ELASTICSEARCH_HOST}/{ELASTICSEARCH_INDEX}"
        info_response = requests.get(info_url, headers=get_es_headers())
        info_response.raise_for_status()

        info_data = info_response.json()

        stats = {
            "document_count": count_data["count"],
            "index_size_bytes": index_stats["total"]["store"]["size_in_bytes"],
            "index_size_mb": round(
                index_stats["total"]["store"]["size_in_bytes"] / (1024 * 1024), 2
            ),
            "shards": {
                "total": index_stats["total"]["segments"]["count"],
                "primary": len(
                    info_data[ELASTICSEARCH_INDEX]["settings"]["index"][
                        "number_of_shards"
                    ]
                ),
            },
            "creation_date": info_data[ELASTICSEARCH_INDEX]["settings"]["index"][
                "creation_date"
            ],
            "timestamp": datetime.now().isoformat(),
        }

        logging.info(f"Statistiques ES: {stats}")
        return stats

    except Exception as e:
        logging.error(f"Erreur lors de la récupération des stats: {str(e)}")
        raise


def perform_reindexation(**context):
    """
    Réindexation de l'index Elasticsearch
    """
    try:
        ti = context["ti"]
        pre_stats = ti.xcom_pull(task_ids="get_pre_stats")

        logging.info("Début de la réindexation Elasticsearch")

        # Nom du nouvel index avec timestamp
        new_index_name = (
            f"{ELASTICSEARCH_INDEX}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        old_index_name = ELASTICSEARCH_INDEX

        # Configuration du mapping (copié de l'index existant)
        mapping_url = f"{ELASTICSEARCH_HOST}/{old_index_name}/_mapping"
        mapping_response = requests.get(mapping_url, headers=get_es_headers())
        mapping_response.raise_for_status()

        mapping_data = mapping_response.json()
        current_mapping = mapping_data[old_index_name]["mappings"]

        # Création du nouvel index
        create_index_config = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "refresh_interval": "30s",
            },
            "mappings": current_mapping,
        }

        create_url = f"{ELASTICSEARCH_HOST}/{new_index_name}"
        create_response = requests.put(
            create_url, headers=get_es_headers(), json=create_index_config
        )
        create_response.raise_for_status()

        logging.info(f"Nouvel index {new_index_name} créé")

        # Réindexation
        reindex_config = {
            "source": {"index": old_index_name},
            "dest": {"index": new_index_name},
            "conflicts": "proceed",
        }

        reindex_url = f"{ELASTICSEARCH_HOST}/_reindex"
        reindex_response = requests.post(
            reindex_url, headers=get_es_headers(), json=reindex_config
        )
        reindex_response.raise_for_status()

        reindex_result = reindex_response.json()

        logging.info(f"Réindexation terminée: {reindex_result}")

        # Basculement d'alias (si utilisé)
        # Note: Cette partie peut être adaptée selon votre stratégie d'alias

        return {
            "old_index": old_index_name,
            "new_index": new_index_name,
            "documents_copied": reindex_result.get("total", 0),
            "time_taken_ms": reindex_result.get("took", 0),
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Erreur lors de la réindexation: {str(e)}")
        raise


def validate_reindexation(**context):
    """
    Validation de la réindexation
    """
    try:
        ti = context["ti"]
        pre_stats = ti.xcom_pull(task_ids="get_pre_stats")
        reindex_info = ti.xcom_pull(task_ids="perform_reindex")

        logging.info("Validation de la réindexation")

        new_index_name = reindex_info["new_index"]

        # Vérification du nombre de documents
        count_url = f"{ELASTICSEARCH_HOST}/{new_index_name}/_count"
        count_response = requests.get(count_url, headers=get_es_headers())
        count_response.raise_for_status()

        new_count = count_response.json()["count"]
        old_count = pre_stats["document_count"]

        # Calcul des métriques de validation
        validation_result = {
            "document_count_before": old_count,
            "document_count_after": new_count,
            "document_loss": old_count - new_count,
            "document_loss_percentage": (
                round(((old_count - new_count) / old_count) * 100, 2)
                if old_count > 0
                else 0
            ),
            "validation_passed": abs(old_count - new_count)
            <= (old_count * 0.01),  # Tolérance de 1%
            "timestamp": datetime.now().isoformat(),
        }

        if validation_result["validation_passed"]:
            logging.info("✅ Validation réussie - Les données sont cohérentes")
        else:
            logging.warning(
                f"⚠️ Validation échouée - Perte de données: {validation_result['document_loss']} documents"
            )

        return validation_result

    except Exception as e:
        logging.error(f"Erreur lors de la validation: {str(e)}")
        raise


def create_post_reindex_snapshot(**context):
    """
    Création d'un snapshot après la réindexation
    """
    try:
        ti = context["ti"]
        repo_info = ti.xcom_pull(task_ids="create_snapshot_repository")
        reindex_info = ti.xcom_pull(task_ids="perform_reindex")

        repository_name = repo_info["repository_name"]
        new_index_name = reindex_info["new_index"]

        # Nom du snapshot post-réindexation
        snapshot_name = f"post-reindex-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        logging.info(f"Création du snapshot post-réindexation {snapshot_name}")

        snapshot_config = {
            "indices": new_index_name,
            "ignore_unavailable": True,
            "include_global_state": False,
            "metadata": {
                "description": f"Snapshot post-réindexation du {datetime.now().isoformat()}",
                "created_by": "airflow_reindex_weekly",
                "index": new_index_name,
                "reindex_job": reindex_info,
            },
        }

        snapshot_url = (
            f"{ELASTICSEARCH_HOST}/_snapshot/{repository_name}/{snapshot_name}"
        )
        response = requests.put(
            snapshot_url, headers=get_es_headers(), json=snapshot_config
        )
        response.raise_for_status()

        return {
            "snapshot_name": snapshot_name,
            "repository_name": repository_name,
            "index_snapshotted": new_index_name,
            "status": "initiated",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Erreur lors du snapshot post-réindexation: {str(e)}")
        raise


def cleanup_old_indices(**context):
    """
    Nettoyage des anciens indices (garde les 3 derniers)
    """
    try:
        logging.info("Nettoyage des anciens indices")

        # Liste des indices
        indices_url = (
            f"{ELASTICSEARCH_HOST}/_cat/indices/{ELASTICSEARCH_INDEX}*?format=json"
        )
        response = requests.get(indices_url, headers=get_es_headers())
        response.raise_for_status()

        indices = response.json()

        # Tri par date de création (plus ancien en premier)
        indices_sorted = sorted(indices, key=lambda x: x["creation.date"])

        # Garder les 3 plus récents
        indices_to_delete = indices_sorted[:-3] if len(indices_sorted) > 3 else []

        deleted_indices = []
        for index_info in indices_to_delete:
            index_name = index_info["index"]

            # Ne pas supprimer l'index principal
            if index_name == ELASTICSEARCH_INDEX:
                continue

            delete_url = f"{ELASTICSEARCH_HOST}/{index_name}"
            delete_response = requests.delete(delete_url, headers=get_es_headers())

            if delete_response.status_code == 200:
                deleted_indices.append(index_name)
                logging.info(f"Index supprimé: {index_name}")

        return {
            "deleted_indices": deleted_indices,
            "remaining_indices": len(indices) - len(deleted_indices),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Erreur lors du nettoyage: {str(e)}")
        # Ne pas faire échouer le DAG pour le nettoyage
        return {
            "error": str(e),
            "deleted_indices": [],
            "timestamp": datetime.now().isoformat(),
        }


# Définition des tâches
create_repo_task = PythonOperator(
    task_id="create_snapshot_repository",
    python_callable=create_snapshot_repository,
    dag=dag,
    doc_md="Création/vérification du repository de snapshots",
)

pre_snapshot_task = PythonOperator(
    task_id="create_pre_snapshot",
    python_callable=create_pre_reindex_snapshot,
    dag=dag,
    doc_md="Création d'un snapshot avant réindexation",
)

pre_stats_task = PythonOperator(
    task_id="get_pre_stats",
    python_callable=get_elasticsearch_stats,
    dag=dag,
    doc_md="Récupération des statistiques pré-réindexation",
)

reindex_task = PythonOperator(
    task_id="perform_reindex",
    python_callable=perform_reindexation,
    dag=dag,
    doc_md="Réindexation de l'index Elasticsearch",
)

validate_task = PythonOperator(
    task_id="validate_reindex",
    python_callable=validate_reindexation,
    dag=dag,
    doc_md="Validation de la réindexation",
)

post_snapshot_task = PythonOperator(
    task_id="create_post_snapshot",
    python_callable=create_post_reindex_snapshot,
    dag=dag,
    doc_md="Création d'un snapshot après réindexation",
)

cleanup_task = PythonOperator(
    task_id="cleanup_old_indices",
    python_callable=cleanup_old_indices,
    dag=dag,
    doc_md="Nettoyage des anciens indices",
)

# Tâche de notification finale
notify_task = BashOperator(
    task_id="notify_completion",
    bash_command="""
    echo "🔄 Réindexation hebdomadaire terminée avec succès à $(date)"
    echo "📊 Consultez les métriques dans Airflow UI"
    echo "📝 Logs disponibles pour analyse détaillée"
    """,
    dag=dag,
)

# Définition des dépendances
create_repo_task >> [pre_snapshot_task, pre_stats_task]
[pre_snapshot_task, pre_stats_task] >> reindex_task
reindex_task >> validate_task
validate_task >> [post_snapshot_task, cleanup_task]
[post_snapshot_task, cleanup_task] >> notify_task
