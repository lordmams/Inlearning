#!/usr/bin/env python3
"""
Tâches Elasticsearch pour l'orchestration simple
"""

import requests
import logging
import os
import sys
from datetime import datetime

logger = logging.getLogger(__name__)


def run_elasticsearch_reindex():
    """Réindexation hebdomadaire d'Elasticsearch"""
    try:
        logger.info("Démarrage de la réindexation Elasticsearch")

        # Configuration Elasticsearch
        es_host = os.getenv(
            "ELASTICSEARCH_HOST",
            "https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443",
        )
        es_index = os.getenv("ELASTICSEARCH_INDEX", "inlearning-storage")
        es_api_key = os.getenv(
            "ELASTICSEARCH_API_KEY",
            "T2FIYU5Ka0J5U1pfX01EQTN5QzY6XzJoOVZRTHp4Wk9EZ0V1T0dNV0ZGQQ==",
        )

        headers = {
            "Authorization": f"ApiKey {es_api_key}",
            "Content-Type": "application/json",
        }

        # 1. Créer un snapshot avant la réindexation
        snapshot_name = f"pre_reindex_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        snapshot_body = {
            "indices": es_index,
            "ignore_unavailable": True,
            "include_global_state": False,
        }

        # 2. Obtenir les statistiques actuelles
        stats_url = f"{es_host}/{es_index}/_stats"
        response = requests.get(stats_url, headers=headers)

        if response.status_code == 200:
            stats = response.json()
            doc_count = stats["indices"][es_index]["total"]["docs"]["count"]
            logger.info(f"Documents actuels dans {es_index}: {doc_count}")
        else:
            logger.warning(
                f"Impossible d'obtenir les statistiques: {response.status_code}"
            )

        # 3. Optimiser l'index
        optimize_url = f"{es_host}/{es_index}/_optimize"
        response = requests.post(optimize_url, headers=headers)

        if response.status_code == 200:
            logger.info("Optimisation de l'index terminée")
        else:
            logger.warning(f"Optimisation échouée: {response.status_code}")

        # 4. Nettoyer les anciens indices
        cleanup_url = f"{es_host}/_cat/indices/{es_index}*?format=json"
        response = requests.get(cleanup_url, headers=headers)

        if response.status_code == 200:
            indices = response.json()
            logger.info(f"Indices trouvés: {len(indices)}")

        logger.info("Réindexation Elasticsearch terminée")
        return True

    except Exception as e:
        logger.error(f"Erreur dans la réindexation Elasticsearch: {e}")
        return False


def run_elasticsearch_health_check():
    """Vérification de santé d'Elasticsearch"""
    try:
        logger.info("Vérification de santé Elasticsearch")

        es_host = os.getenv(
            "ELASTICSEARCH_HOST",
            "https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443",
        )
        es_api_key = os.getenv(
            "ELASTICSEARCH_API_KEY",
            "T2FIYU5Ka0J5U1pfX01EQTN5QzY6XzJoOVZRTHp4Wk9EZ0V1T0dNV0ZGQQ==",
        )

        headers = {
            "Authorization": f"ApiKey {es_api_key}",
            "Content-Type": "application/json",
        }

        # Vérification du cluster
        cluster_url = f"{es_host}/_cluster/health"
        response = requests.get(cluster_url, headers=headers)

        if response.status_code == 200:
            health = response.json()
            status = health.get("status", "unknown")
            logger.info(f"Statut du cluster Elasticsearch: {status}")

            if status in ["green", "yellow"]:
                return True
            else:
                logger.warning(f"Cluster en état: {status}")
                return False
        else:
            logger.error(f"Erreur vérification cluster: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Erreur vérification santé Elasticsearch: {e}")
        return False
