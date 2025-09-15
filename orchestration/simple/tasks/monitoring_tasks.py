#!/usr/bin/env python3
"""
Tâches de monitoring pour l'orchestration simple
"""

import logging
import os
import sys
from datetime import datetime, timedelta

import psutil
import requests

logger = logging.getLogger(__name__)


def run_system_health_check():
    """Vérification de santé du système"""
    try:
        logger.info("Démarrage de la vérification de santé du système")

        health_status = {
            "timestamp": datetime.now().isoformat(),
            "services": {},
            "system": {},
            "overall_status": "healthy",
        }

        # Vérification des services
        services = {
            "django": "http://localhost:8080/admin/",
            "flask_api": "http://localhost:5000/health",
            "elasticsearch": "https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443/_cluster/health",
            "spark": "http://localhost:8090/json/",
            "pgadmin": "http://localhost:8085/misc/ping",
        }

        for service_name, url in services.items():
            try:
                if service_name == "elasticsearch":
                    headers = {
                        "Authorization": f'ApiKey {os.getenv("ELASTICSEARCH_API_KEY", "")}',
                        "Content-Type": "application/json",
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                else:
                    response = requests.get(url, timeout=10)

                if response.status_code in [200, 302]:
                    health_status["services"][service_name] = "healthy"
                    logger.info(f"Service {service_name}: OK")
                else:
                    health_status["services"][service_name] = "unhealthy"
                    logger.warning(f"Service {service_name}: {response.status_code}")

            except Exception as e:
                health_status["services"][service_name] = "unhealthy"
                logger.error(f"Service {service_name}: {e}")

        # Vérification des ressources système
        health_status["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
        }

        # Détermination du statut global
        unhealthy_services = [
            s for s in health_status["services"].values() if s == "unhealthy"
        ]
        if unhealthy_services:
            health_status["overall_status"] = "degraded"

        if (
            health_status["system"]["cpu_percent"] > 90
            or health_status["system"]["memory_percent"] > 90
        ):
            health_status["overall_status"] = "critical"

        logger.info(
            f"Vérification de santé terminée: {health_status['overall_status']}"
        )

        # Sauvegarde du rapport
        report_file = (
            f"logs/health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(report_file, "w") as f:
            import json

            json.dump(health_status, f, indent=2)

        return health_status["overall_status"] == "healthy"

    except Exception as e:
        logger.error(f"Erreur dans la vérification de santé: {e}")
        return False


def run_log_cleanup():
    """Nettoyage des logs anciens"""
    try:
        logger.info("Démarrage du nettoyage des logs")

        logs_dir = "orchestration/simple/logs"
        cutoff_date = datetime.now() - timedelta(days=7)

        if not os.path.exists(logs_dir):
            logger.warning(f"Dossier logs non trouvé: {logs_dir}")
            return False

        cleaned_files = 0

        for filename in os.listdir(logs_dir):
            filepath = os.path.join(logs_dir, filename)

            if os.path.isfile(filepath):
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))

                if file_time < cutoff_date:
                    try:
                        os.remove(filepath)
                        cleaned_files += 1
                        logger.info(f"Fichier supprimé: {filename}")
                    except Exception as e:
                        logger.error(f"Erreur suppression {filename}: {e}")

        logger.info(f"Nettoyage terminé: {cleaned_files} fichiers supprimés")
        return True

    except Exception as e:
        logger.error(f"Erreur dans le nettoyage des logs: {e}")
        return False


def run_performance_monitoring():
    """Monitoring des performances"""
    try:
        logger.info("Démarrage du monitoring des performances")

        # Métriques système
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage("/").total,
                "free": psutil.disk_usage("/").free,
                "percent": psutil.disk_usage("/").percent,
            },
            "network": psutil.net_io_counters()._asdict(),
        }

        # Sauvegarde des métriques
        metrics_file = (
            f"logs/performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(metrics_file, "w") as f:
            import json

            json.dump(metrics, f, indent=2)

        logger.info("Monitoring des performances terminé")
        return True

    except Exception as e:
        logger.error(f"Erreur dans le monitoring des performances: {e}")
        return False
