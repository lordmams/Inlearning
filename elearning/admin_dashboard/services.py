"""
Service de monitoring des services InLearning
Vérifie la santé de tous les services et maintient les statistiques
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import os
import requests
from django.conf import settings
from django.utils import timezone

from .models import ServiceHealthHistory, ServiceMonitoring, SystemAlert

logger = logging.getLogger(__name__)


class ServiceHealthChecker:
    """Service pour vérifier la santé de tous les services"""

    def __init__(self):
        self.timeout = 5  # 5 secondes de timeout
        self.services_config = self._get_services_config()

    def _get_services_config(self) -> List[Dict]:
        """Configuration des services à surveiller"""
        return [
            {
                "name": "Django Application",
                "service_type": "django",
                "url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:8000",
                "health_check_url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:8000/admin/",
                "is_critical": True,
            },
            {
                "name": "Flask API",
                "service_type": "flask_api",
                "url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:5000",
                "health_check_url": "http://flask_api:5000/health",
                "is_critical": True,
            },
            {
                "name": "Elasticsearch",
                "service_type": "elasticsearch",
                "url": "https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443",
                "health_check_url": "https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443",
                "is_critical": True,
            },
            {
                "name": "PostgreSQL",
                "service_type": "postgres",
                "url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:5432",
                "health_check_url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:5432",
                "is_critical": True,
            },
            {
                "name": "Redis",
                "service_type": "redis",
                "url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:6379",
                "health_check_url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:6379",
                "is_critical": True,
            },
            {
                "name": "Python Orchestrator",
                "service_type": "orchestration",
                "url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:8001",
                "health_check_url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:8000/health",
                "is_critical": False,
            },
            {
                "name": "Spark Master",
                "service_type": "spark_master",
                "url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:8090",
                "health_check_url": "http://spark-master:8080/json/",
                "is_critical": False,
            },
            {
                "name": "PgAdmin",
                "service_type": "pgadmin",
                "url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:8085",
                "health_check_url": f"http://{os.environ.get('SERVER_IP', 'localhost')}:80/misc/ping",
                "is_critical": False,
            },
        ]

    def check_service_health(self, service_name: str) -> Dict:
        """
        Vérifie la santé d'un service spécifique par nom
        Returns: dict avec status, response_time_ms, error, etc.
        """
        # Trouver la config du service
        service_config = None
        for config in self.services_config:
            if (
                config.get("service_type") == service_name
                or config.get("name") == service_name
            ):
                service_config = config
                break

        if not service_config:
            return {
                "status": "unknown",
                "response_time_ms": 0,
                "error": f"Service {service_name} not found in configuration",
                "uptime_percentage": 0,
                "time_since_last_check": "Never",
            }

        # Appeler la méthode originale
        status, response_time_ms, error = self._check_service_health_internal(
            service_config
        )

        return {
            "status": status,
            "response_time_ms": response_time_ms,
            "error": error,
            "uptime_percentage": 100 if status == "healthy" else 0,
            "time_since_last_check": "Just now",
        }

    def _check_service_health_internal(
        self, service_config: Dict
    ) -> Tuple[str, int, str]:
        """
        Vérifie la santé d'un service spécifique (méthode interne)
        Returns: (status, response_time_ms, error_message)
        """
        try:
            start_time = time.time()

            # Méthodes spéciales pour certains services
            if service_config["service_type"] == "postgres":
                return self._check_postgres_health()
            elif service_config["service_type"] == "redis":
                return self._check_redis_health()
            elif service_config["service_type"] == "orchestration":
                return self._check_orchestration_health()
            elif service_config["service_type"] == "pgadmin":
                return self._check_pgadmin_health()
            else:
                # Check HTTP standard
                response = requests.get(
                    service_config["health_check_url"],
                    timeout=self.timeout,
                    verify=False,  # Pour Elasticsearch cloud
                )
                response_time = int((time.time() - start_time) * 1000)

                # Analyser la réponse selon le type de service
                if service_config["service_type"] == "elasticsearch":
                    return self._analyze_elasticsearch_response(response, response_time)
                elif service_config["service_type"] == "spark_master":
                    return self._analyze_spark_response(response, response_time)
                elif service_config["service_type"] == "flask_api":
                    return self._analyze_flask_response(response, response_time)
                else:
                    # Check HTTP standard
                    if response.status_code == 200:
                        return "healthy", response_time, ""
                    elif 200 <= response.status_code < 300:
                        return "healthy", response_time, ""
                    elif 300 <= response.status_code < 500:
                        return "degraded", response_time, f"HTTP {response.status_code}"
                    else:
                        return (
                            "unhealthy",
                            response_time,
                            f"HTTP {response.status_code}",
                        )

        except requests.exceptions.ConnectionError:
            return "unhealthy", 0, "Connection refused"
        except requests.exceptions.Timeout:
            return "degraded", self.timeout * 1000, "Timeout"
        except Exception as e:
            return "unhealthy", 0, str(e)

    def check_all_services(self) -> List[Dict]:
        """Vérifie la santé de tous les services configurés"""
        results = []

        for service_config in self.services_config:
            try:
                status, response_time, error_message = self._check_service_health_internal(
                    service_config
                )

                result = {
                    "name": service_config["name"],
                    "service_type": service_config["service_type"],
                    "status": status,
                    "response_time": response_time,
                    "error_message": error_message,
                    "url": service_config["url"],
                    "is_critical": service_config["is_critical"],
                    "last_check": timezone.now(),
                }

                results.append(result)

                # Log du résultat
                logger.info(f"{service_config['name']}: {status} ({response_time}ms)")

            except Exception as e:
                logger.error(
                    f"Erreur lors de la vérification de {service_config['name']}: {e}"
                )
                result = {
                    "name": service_config["name"],
                    "service_type": service_config["service_type"],
                    "status": "unhealthy",
                    "response_time": 0,
                    "error_message": str(e),
                    "url": service_config["url"],
                    "is_critical": service_config["is_critical"],
                    "last_check": timezone.now(),
                }
                results.append(result)

        return results

    def get_system_overview(self) -> Dict:
        """Retourne un aperçu général du système"""
        try:
            results = self.check_all_services()

            total_services = len(results)
            healthy_services = len([r for r in results if r["status"] == "healthy"])
            degraded_services = len([r for r in results if r["status"] == "degraded"])
            unhealthy_services = len([r for r in results if r["status"] == "unhealthy"])
            critical_unhealthy = len(
                [r for r in results if r["status"] == "unhealthy" and r["is_critical"]]
            )

            # Calculer le pourcentage de santé
            health_percentage = (
                (healthy_services / total_services * 100) if total_services > 0 else 0
            )

            # Déterminer le statut global
            if critical_unhealthy > 0:
                overall_status = "critical"
            elif unhealthy_services > 0:
                overall_status = "degraded"
            elif degraded_services > 0:
                overall_status = "warning"
            else:
                overall_status = "healthy"

            return {
                "overall_status": overall_status,
                "health_percentage": round(health_percentage, 1),
                "total_services": total_services,
                "healthy_services": healthy_services,
                "degraded_services": degraded_services,
                "unhealthy_services": unhealthy_services,
                "critical_unhealthy": critical_unhealthy,
                "last_check": timezone.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Erreur lors de la génération de l'aperçu système: {e}")
            return {
                "overall_status": "error",
                "health_percentage": 0,
                "total_services": 0,
                "healthy_services": 0,
                "degraded_services": 0,
                "unhealthy_services": 0,
                "critical_unhealthy": 0,
                "last_check": timezone.now().isoformat(),
                "error": str(e),
            }

    def _check_postgres_health(self) -> Tuple[str, int, str]:
        """Vérifie PostgreSQL via Django ORM"""
        try:
            from django.db import connection

            start_time = time.time()

            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

            response_time = int((time.time() - start_time) * 1000)
            return "healthy", response_time, ""

        except Exception as e:
            return "unhealthy", 0, str(e)

    def _check_redis_health(self) -> Tuple[str, int, str]:
        """Vérifie Redis via Django cache"""
        try:
            from django.core.cache import cache

            start_time = time.time()

            # Test simple de cache
            cache.set("health_check", "ok", 10)
            result = cache.get("health_check")

            response_time = int((time.time() - start_time) * 1000)

            if result == "ok":
                return "healthy", response_time, ""
            else:
                return "unhealthy", response_time, "Cache test failed"

        except Exception as e:
            return "unhealthy", 0, str(e)

    def _check_orchestration_health(self) -> Tuple[str, int, str]:
        """Vérifie le Python Orchestrator"""
        try:
            start_time = time.time()
            response = requests.get(
                "http://inlearning-orchestration:8000/health", timeout=self.timeout
            )
            response_time = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return "healthy", response_time, "Orchestrator running"
            else:
                return "unhealthy", response_time, f"HTTP {response.status_code}"

        except Exception as e:
            return "unhealthy", 0, str(e)

    def _check_pgadmin_health(self) -> Tuple[str, int, str]:
        """Vérifie PgAdmin"""
        try:
            start_time = time.time()
            response = requests.get("http://pgadmin:80/misc/ping", timeout=self.timeout)
            response_time = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return "healthy", response_time, "PgAdmin accessible"
            else:
                return "unhealthy", response_time, f"HTTP {response.status_code}"

        except Exception as e:
            return "unhealthy", 0, str(e)

    def _analyze_elasticsearch_response(
        self, response, response_time
    ) -> Tuple[str, int, str]:
        """Analyse la réponse d'Elasticsearch - vérification simple"""
        try:
            # Si on reçoit une réponse (même avec erreur d'auth), Elasticsearch est accessible
            if response.status_code in [200, 401, 403]:
                return "healthy", response_time, "Elasticsearch cloud accessible"
            else:
                return "unhealthy", response_time, f"HTTP {response.status_code}"

        except Exception as e:
            return "unhealthy", response_time, str(e)

    def _analyze_flask_response(self, response, response_time) -> Tuple[str, int, str]:
        """Analyse la réponse de Flask API"""
        try:
            if response.status_code == 200:
                data = response.json()

                # Vérifier le statut Spark si disponible
                spark_status = data.get("spark_cluster", {}).get("status", "unknown")
                message = f"Spark: {spark_status}" if spark_status != "unknown" else ""

                return "healthy", response_time, message
            else:
                return "unhealthy", response_time, f"HTTP {response.status_code}"

        except Exception as e:
            return "healthy", response_time, "API OK (JSON parse error)"

    def _analyze_spark_response(self, response, response_time) -> Tuple[str, int, str]:
        """Analyse la réponse de Spark Master"""
        try:
            if response.status_code == 200:
                data = response.json()
                alive_workers = data.get("aliveworkers", 0)

                if alive_workers >= 2:
                    return "healthy", response_time, f"{alive_workers} workers"
                elif alive_workers >= 1:
                    return "degraded", response_time, f"Only {alive_workers} worker"
                else:
                    return "unhealthy", response_time, "No workers available"
            else:
                return "unhealthy", response_time, f"HTTP {response.status_code}"

        except Exception as e:
            return "unhealthy", response_time, str(e)


# Instance globale du checker
health_checker = ServiceHealthChecker()


def update_service_status():
    """
    Function to manually trigger service status update
    """
    try:
        logger.info("🔄 Démarrage de la mise à jour manuelle des services...")
        
        # Check all services
        health_checker.check_all_services()
        
        logger.info("✅ Mise à jour des services terminée avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la mise à jour des services: {e}")
        return False


def get_system_health_summary():
    """
    Get a summary of system health
    """
    try:
        healthy_count = ServiceMonitoring.objects.filter(status='healthy').count()
        total_count = ServiceMonitoring.objects.count()
        
        return {
            'healthy': healthy_count,
            'total': total_count,
            'health_score': (healthy_count / total_count * 100) if total_count > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting system health summary: {e}")
        return {'healthy': 0, 'total': 0, 'health_score': 0}



def get_system_health_summary():
    """
    Get a summary of system health
    """
    try:
        healthy_count = ServiceMonitoring.objects.filter(status="healthy").count()
        total_count = ServiceMonitoring.objects.count()
        
        return {
            "healthy": healthy_count,
            "total": total_count,
            "health_score": (healthy_count / total_count * 100) if total_count > 0 else 0
        }
    except Exception as e:
        logger.error(f"Error getting system health summary: {e}")
        return {"healthy": 0, "total": 0, "health_score": 0}


def update_and_save_services():
    """
    Met à jour et sauvegarde tous les services en base de données
    """
    try:
        from .models import ServiceMonitoring, ServiceHealthHistory
        
        logger.info("🔄 Mise à jour et sauvegarde des services...")
        
        # Obtenir les résultats des checks
        results = health_checker.check_all_services()
        
        for result in results:
            # Créer ou mettre à jour le service
            service, created = ServiceMonitoring.objects.get_or_create(
                name=result["name"],
                defaults={
                    'service_type': result["service_type"],
                    'url': result["url"],
                    'health_check_url': result["url"],  # Utiliser l'URL par défaut
                    'is_critical': result["is_critical"],
                    'status': result["status"],
                    'response_time_ms': result["response_time"],
                    'error_message': result["error_message"],
                    'last_check': result["last_check"]
                }
            )
            
            if not created:
                # Mettre à jour le service existant
                service.status = result["status"]
                service.response_time_ms = result["response_time"]
                service.error_message = result["error_message"]
                service.last_check = result["last_check"]
                service.save()
            
            # Ajouter à l'historique
            ServiceHealthHistory.objects.create(
                service=service,
                status=result["status"],
                response_time_ms=result["response_time"],
                error_message=result["error_message"]
            )
            
            logger.info(f"💾 {service.name}: {service.status} sauvegardé")
        
        logger.info("✅ Sauvegarde terminée avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde: {e}")
        return False
