from django.db import models
from django.utils import timezone
from datetime import timedelta


class ServiceMonitoring(models.Model):
    """Modèle pour surveiller l'état des services"""

    SERVICE_TYPES = [
        ("django", "Django Application"),
        ("flask_api", "Flask API"),
        ("elasticsearch", "Elasticsearch"),
        ("postgres", "PostgreSQL"),
        ("redis", "Redis"),
        ("orchestration", "Python Orchestrator"),
        ("spark_master", "Spark Master"),
        ("spark_worker", "Spark Worker"),
        ("pgadmin", "PgAdmin"),
        ("consumer", "File Consumer"),
    ]

    STATUS_CHOICES = [
        ("healthy", "Healthy"),
        ("degraded", "Degraded"),
        ("unhealthy", "Unhealthy"),
        ("unknown", "Unknown"),
    ]

    name = models.CharField(max_length=100, unique=True)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES)
    url = models.URLField(help_text="URL principale du service")
    health_check_url = models.URLField(
        help_text="URL pour vérifier la santé du service"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unknown")
    last_check = models.DateTimeField(null=True, blank=True)
    response_time_ms = models.IntegerField(
        null=True, blank=True, help_text="Temps de réponse en millisecondes"
    )
    error_message = models.TextField(blank=True, help_text="Dernier message d'erreur")
    uptime_percentage = models.FloatField(
        default=0.0, help_text="Pourcentage de disponibilité sur 24h"
    )
    is_critical = models.BooleanField(
        default=True, help_text="Service critique pour le système"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["service_type", "name"]
        verbose_name = "Service Monitoring"
        verbose_name_plural = "Services Monitoring"

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def is_healthy(self):
        """Vérifie si le service est en bonne santé"""
        return self.status == "healthy"

    def time_since_last_check(self):
        """Retourne le temps écoulé depuis la dernière vérification"""
        if not self.last_check:
            return "Jamais vérifié"

        delta = timezone.now() - self.last_check
        if delta.total_seconds() < 60:
            return f"{int(delta.total_seconds())}s"
        elif delta.total_seconds() < 3600:
            return f"{int(delta.total_seconds() / 60)}min"
        else:
            return f"{int(delta.total_seconds() / 3600)}h"


class ServiceHealthHistory(models.Model):
    """Historique des vérifications de santé des services"""

    service = models.ForeignKey(
        ServiceMonitoring, on_delete=models.CASCADE, related_name="health_history"
    )
    status = models.CharField(max_length=20, choices=ServiceMonitoring.STATUS_CHOICES)
    response_time_ms = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Service Health History"
        verbose_name_plural = "Services Health History"

    def __str__(self):
        return f"{self.service.name} - {self.get_status_display()} at {self.timestamp}"


class SystemAlert(models.Model):
    """Alertes système pour les problèmes détectés"""

    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("critical", "Critical"),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    service = models.ForeignKey(
        ServiceMonitoring, on_delete=models.CASCADE, null=True, blank=True
    )
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "System Alert"
        verbose_name_plural = "System Alerts"

    def __str__(self):
        return f"{self.get_severity_display()}: {self.title}"

    def resolve(self):
        """Marque l'alerte comme résolue"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.save()
