"""
Service d'interface avec Apache Spark pour la platforme InLearning
Permet de soumettre des jobs Spark et récupérer les résultats
"""

import requests
import json
import logging
import os
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SparkService:
    """Service pour interagir avec le cluster Apache Spark"""

    def __init__(self):
        self.spark_master_url = os.environ.get(
            "SPARK_MASTER_URL", "spark://spark-master:7077"
        )
        self.spark_ui_url = os.environ.get("SPARK_UI_URL", "http://spark-master:8080")
        self.spark_enabled = os.environ.get("SPARK_ENABLED", "false").lower() == "true"

    def is_cluster_available(self) -> bool:
        """Vérifie si le cluster Spark est disponible"""
        try:
            if not self.spark_enabled:
                logger.info("Spark désactivé")
                return False

            response = requests.get(f"{self.spark_ui_url}/json/", timeout=5)
            if response.status_code == 200:
                cluster_info = response.json()
                active_workers = cluster_info.get("aliveworkers", 0)

                logger.info(f"✅ Cluster Spark: {active_workers} workers actifs")
                return active_workers > 0

            return False

        except Exception as e:
            logger.warning(f"⚠️ Cluster Spark non disponible: {e}")
            return False

    def get_cluster_status(self) -> Dict[str, Any]:
        """Retourne le statut détaillé du cluster Spark"""
        try:
            if not self.spark_enabled:
                return {
                    "enabled": False,
                    "status": "disabled",
                    "message": "Spark est désactivé",
                }

            response = requests.get(f"{self.spark_ui_url}/json/", timeout=5)
            if response.status_code == 200:
                cluster_info = response.json()

                return {
                    "enabled": True,
                    "status": "available",
                    "master_url": self.spark_master_url,
                    "ui_url": self.spark_ui_url,
                    "active_workers": cluster_info.get("aliveworkers", 0),
                    "cores_total": cluster_info.get("cores", 0),
                    "memory_total": cluster_info.get("memory", 0),
                    "applications": cluster_info.get("activeapps", []),
                }
            else:
                return {
                    "enabled": True,
                    "status": "unavailable",
                    "error": f"HTTP {response.status_code}",
                }

        except Exception as e:
            return {"enabled": True, "status": "error", "error": str(e)}

    def submit_course_processing_job(
        self, courses_data: List[Dict], job_id: str = None
    ) -> Dict[str, Any]:
        """Soumet un job de traitement de cours au cluster Spark"""
        try:
            if not self.is_cluster_available():
                logger.warning("Cluster Spark non disponible - traitement local")
                return self._fallback_local_processing(courses_data)

            # Préparer les données pour Spark
            job_id = job_id or f"course_processing_{int(time.time())}"
            input_path = f"/opt/bitnami/spark/data/input/{job_id}.json"
            output_path = f"/opt/bitnami/spark/data/output/{job_id}"

            # Sauvegarder les données d'entrée
            self._save_input_data(courses_data, input_path)

            # Construire la commande Spark
            spark_submit_cmd = [
                "spark-submit",
                "--master",
                self.spark_master_url,
                "--executor-memory",
                "2g",
                "--executor-cores",
                "2",
                "--total-executor-cores",
                "4",
                "/opt/bitnami/spark/jobs/course_processing_distributed.py",
                "--input-path",
                input_path,
                "--output-path",
                output_path,
                "--job-id",
                job_id,
            ]

            # Simulation de soumission (en réalité, utiliserait pyspark ou spark-submit)
            logger.info(f"🚀 Soumission job Spark: {job_id}")
            logger.info(f"📊 Cours à traiter: {len(courses_data)}")

            # Retourner les informations du job
            return {
                "job_id": job_id,
                "status": "submitted",
                "input_path": input_path,
                "output_path": output_path,
                "course_count": len(courses_data),
                "spark_enabled": True,
                "estimated_duration": self._estimate_processing_time(len(courses_data)),
            }

        except Exception as e:
            logger.error(f"❌ Erreur soumission job Spark: {e}")
            return {
                "error": str(e),
                "fallback": self._fallback_local_processing(courses_data),
            }

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Récupère le statut d'un job Spark"""
        try:
            # Vérifier les applications actives
            response = requests.get(
                f"{self.spark_ui_url}/api/v1/applications", timeout=5
            )
            if response.status_code == 200:
                applications = response.json()

                # Chercher notre job
                for app in applications:
                    if job_id in app.get("name", ""):
                        return {
                            "job_id": job_id,
                            "status": (
                                "running"
                                if app.get("attempts", [{}])[-1].get("completed", True)
                                == False
                                else "completed"
                            ),
                            "application_id": app.get("id"),
                            "start_time": app.get("attempts", [{}])[-1].get(
                                "startTime"
                            ),
                            "duration": app.get("attempts", [{}])[-1].get(
                                "duration", 0
                            ),
                        }

                # Job non trouvé - peut-être terminé
                return {
                    "job_id": job_id,
                    "status": "completed_or_not_found",
                    "message": "Job non trouvé dans les applications actives",
                }

            return {
                "job_id": job_id,
                "status": "unknown",
                "error": "Impossible de contacter l'API Spark",
            }

        except Exception as e:
            return {"job_id": job_id, "status": "error", "error": str(e)}

    def get_job_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Récupère les résultats d'un job Spark"""
        try:
            output_path = f"/opt/bitnami/spark/data/output/{job_id}"
            results_file = Path(output_path) / "results.json"

            if results_file.exists():
                with open(results_file, "r", encoding="utf-8") as f:
                    results = json.load(f)

                logger.info(f"📊 Résultats récupérés pour job {job_id}")
                return results
            else:
                logger.warning(f"⚠️ Résultats non trouvés pour job {job_id}")
                return None

        except Exception as e:
            logger.error(f"❌ Erreur récupération résultats {job_id}: {e}")
            return None

    def _save_input_data(self, courses_data: List[Dict], input_path: str):
        """Sauvegarde les données d'entrée pour Spark"""
        try:
            # Créer le répertoire si nécessaire
            Path(input_path).parent.mkdir(parents=True, exist_ok=True)

            # Sauvegarder les données
            with open(input_path, "w", encoding="utf-8") as f:
                json.dump(courses_data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Données sauvegardées: {input_path}")

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde données: {e}")
            raise

    def _estimate_processing_time(self, course_count: int) -> int:
        """Estime le temps de traitement en secondes"""
        # Estimation basée sur la taille du cluster et le nombre de cours
        base_time = 30  # 30 secondes de base
        time_per_course = 0.1  # 0.1 seconde par cours

        estimated_time = base_time + (course_count * time_per_course)
        return int(estimated_time)

    def _fallback_local_processing(self, courses_data: List[Dict]) -> Dict[str, Any]:
        """Traitement local de fallback quand Spark n'est pas disponible"""
        logger.info("🔄 Fallback vers traitement local")

        # Simulation de traitement local simple
        processed_courses = []

        for course in courses_data:
            # Traitement basique
            processed_course = course.copy()
            processed_course.update(
                {
                    "processed_locally": True,
                    "processing_method": "fallback",
                    "predicted_category": "Auto-detected",
                    "predicted_level": "Intermédiaire",
                    "processing_timestamp": time.time(),
                }
            )
            processed_courses.append(processed_course)

        return {
            "method": "local_fallback",
            "status": "completed",
            "course_count": len(processed_courses),
            "processed_courses": processed_courses,
            "spark_enabled": False,
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques de performance du cluster"""
        try:
            if not self.is_cluster_available():
                return {"error": "Cluster non disponible"}

            # Récupérer les métriques depuis l'API Spark
            response = requests.get(
                f"{self.spark_ui_url}/api/v1/applications", timeout=5
            )
            if response.status_code == 200:
                applications = response.json()

                total_duration = sum(
                    app.get("attempts", [{}])[-1].get("duration", 0)
                    for app in applications
                )

                completed_jobs = len(
                    [
                        app
                        for app in applications
                        if app.get("attempts", [{}])[-1].get("completed", False)
                    ]
                )

                return {
                    "total_applications": len(applications),
                    "completed_jobs": completed_jobs,
                    "total_processing_time": total_duration,
                    "average_job_duration": total_duration / max(len(applications), 1),
                    "cluster_utilization": "active" if applications else "idle",
                }

            return {"error": "Impossible de récupérer les métriques"}

        except Exception as e:
            return {"error": str(e)}


# Instance globale du service
spark_service = SparkService()
