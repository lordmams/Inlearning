#!/usr/bin/env python3
"""
Système d'orchestration simple pour InLearning Platform
Remplace Airflow avec une approche plus légère et fiable
"""

import schedule
import time
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/scheduler.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class SimpleScheduler:
    def __init__(self):
        self.tasks = {}
        self.running = False

    def register_task(self, name, func, schedule_time, description=""):
        """Enregistre une tâche avec son planning"""
        self.tasks[name] = {
            "function": func,
            "schedule": schedule_time,
            "description": description,
            "last_run": None,
            "status": "registered",
        }
        logger.info(f"Tâche '{name}' enregistrée: {description}")

    def run_task(self, task_name):
        """Exécute une tâche spécifique"""
        if task_name not in self.tasks:
            logger.error(f"Tâche '{task_name}' non trouvée")
            return False

        task = self.tasks[task_name]
        logger.info(f"Démarrage de la tâche: {task_name}")

        try:
            task["status"] = "running"
            task["last_run"] = datetime.now()

            # Exécution de la tâche
            result = task["function"]()

            task["status"] = "completed"
            logger.info(f"Tâche '{task_name}' terminée avec succès")
            return True

        except Exception as e:
            task["status"] = "failed"
            logger.error(f"Erreur dans la tâche '{task_name}': {e}")
            return False

    def get_status(self):
        """Retourne le statut de toutes les tâches"""
        return {
            name: {
                "status": task["status"],
                "last_run": task["last_run"],
                "description": task["description"],
            }
            for name, task in self.tasks.items()
        }

    def start(self):
        """Démarre le scheduler"""
        self.running = True
        logger.info("Démarrage du scheduler d'orchestration")

        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Vérification toutes les minutes
            except KeyboardInterrupt:
                logger.info("Arrêt du scheduler demandé")
                self.running = False
            except Exception as e:
                logger.error(f"Erreur dans le scheduler: {e}")
                time.sleep(60)


def start_health_server():
    """Démarre le serveur de santé en arrière-plan"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import json

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()

                response = {
                    "status": "healthy",
                    "service": "Python Orchestrator",
                    "timestamp": datetime.now().isoformat(),
                    "uptime": "running",
                    "tasks_registered": len(scheduler.tasks),
                }

                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("0.0.0.0", 8000), HealthHandler)
    logger.info("Serveur de santé démarré sur le port 8000")
    server.serve_forever()


# Instance globale du scheduler
scheduler = SimpleScheduler()

if __name__ == "__main__":
    # Import des tâches
    import sys
    import os

    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from tasks import etl_tasks, elasticsearch_tasks, monitoring_tasks

    # Enregistrement des tâches
    scheduler.register_task(
        "etl_users_daily",
        etl_tasks.run_etl_users_daily,
        schedule.every().day.at("02:00"),
        "ETL quotidien des utilisateurs depuis Excel vers PostgreSQL",
    )

    scheduler.register_task(
        "elasticsearch_reindex_weekly",
        elasticsearch_tasks.run_elasticsearch_reindex,
        schedule.every().monday.at("03:00"),
        "Réindexation hebdomadaire d'Elasticsearch",
    )

    scheduler.register_task(
        "system_health_check",
        monitoring_tasks.run_system_health_check,
        schedule.every(30).minutes,
        "Vérification de santé du système toutes les 30 minutes",
    )

    scheduler.register_task(
        "cleanup_logs",
        monitoring_tasks.run_log_cleanup,
        schedule.every().day.at("01:00"),
        "Nettoyage des logs quotidiens",
    )

    # Démarrage du serveur de santé en arrière-plan
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    # Démarrage du scheduler
    scheduler.start()
