import logging
from datetime import datetime
from typing import Any, Dict, List

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class NotificationService:
    """Service de notifications pour les importations de cours"""

    def __init__(self):
        self.email_enabled = getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", False)
        self.admin_emails = getattr(settings, "ADMIN_NOTIFICATION_EMAILS", [])

        # Configuration par défaut
        if not self.admin_emails:
            # Récupérer les emails des superutilisateurs
            self.admin_emails = list(
                User.objects.filter(is_superuser=True, email__isnull=False).values_list(
                    "email", flat=True
                )
            )

    def send_import_success_notification(self, filename: str, result: Dict[str, Any]):
        """
        Envoie une notification de succès d'importation

        Args:
            filename: Nom du fichier importé
            result: Résultat de l'importation
        """
        try:
            subject = f"✅ Importation réussie: {filename}"

            message = self._format_success_message(filename, result)

            # Log local
            logger.info(
                f"Import success: {filename} - {result.get('imported_count', 0)} cours importés"
            )

            # Email si activé
            if self.email_enabled and self.admin_emails:
                self._send_email(subject, message)

            # Autres canaux de notification (Slack, Discord, etc.)
            self._send_webhook_notification(subject, message, "success")

        except Exception as e:
            logger.error(f"Erreur envoi notification succès: {e}")

    def send_import_error_notification(self, filename: str, error: str):
        """
        Envoie une notification d'erreur d'importation

        Args:
            filename: Nom du fichier qui a échoué
            error: Message d'erreur
        """
        try:
            subject = f"❌ Erreur d'importation: {filename}"

            message = self._format_error_message(filename, error)

            # Log local
            logger.error(f"Import error: {filename} - {error}")

            # Email si activé
            if self.email_enabled and self.admin_emails:
                self._send_email(subject, message, priority="high")

            # Autres canaux de notification
            self._send_webhook_notification(subject, message, "error")

        except Exception as e:
            logger.error(f"Erreur envoi notification erreur: {e}")

    def send_consumer_status_notification(self, status: str, message: str):
        """
        Envoie une notification sur l'état du consumer

        Args:
            status: État du consumer (started, stopped, error)
            message: Message détaillé
        """
        try:
            if status == "started":
                subject = "🚀 Consumer de cours démarré"
                emoji = "✅"
            elif status == "stopped":
                subject = "⏹️ Consumer de cours arrêté"
                emoji = "⚠️"
            elif status == "error":
                subject = "🚨 Erreur du consumer de cours"
                emoji = "❌"
            else:
                subject = f"📢 Consumer de cours: {status}"
                emoji = "ℹ️"

            formatted_message = f"""
{emoji} Consumer Status Update

Status: {status.upper()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Message: {message}

---
E-Learning Platform Automation
            """.strip()

            # Log local
            logger.info(f"Consumer status: {status} - {message}")

            # Email pour les erreurs critiques uniquement
            if status == "error" and self.email_enabled and self.admin_emails:
                self._send_email(subject, formatted_message, priority="high")

            # Webhook pour tous les statuts
            self._send_webhook_notification(subject, formatted_message, status)

        except Exception as e:
            logger.error(f"Erreur envoi notification statut: {e}")

    def _format_success_message(self, filename: str, result: Dict[str, Any]) -> str:
        """Formate le message de succès"""
        return f"""
✅ Importation Réussie

Fichier: {filename}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 Résultats:
• Cours importés: {result.get('imported_count', 0)}
• Cours mis à jour: {result.get('updated_count', 0)}
• Cours ignorés: {result.get('skipped_count', 0)}
• Total traité: {result.get('total_processed', 0)}

⚠️ Avertissements: {len(result.get('warnings', []))}
{chr(10).join(f"  - {w}" for w in result.get('warnings', [])[:5])}

---
E-Learning Platform - Import Automation
        """.strip()

    def _format_error_message(self, filename: str, error: str) -> str:
        """Formate le message d'erreur"""
        return f"""
❌ Échec d'Importation

Fichier: {filename}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🚨 Erreur:
{error}

🔧 Actions recommandées:
1. Vérifier le format du fichier
2. Contrôler les permissions d'accès
3. Examiner les logs détaillés
4. Réessayer l'importation si nécessaire

---
E-Learning Platform - Import Automation
        """.strip()

    def _send_email(self, subject: str, message: str, priority: str = "normal"):
        """
        Envoie un email de notification

        Args:
            subject: Sujet de l'email
            message: Corps du message
            priority: Priorité (normal, high)
        """
        try:
            if not self.email_enabled or not self.admin_emails:
                return

            # Ajouter la priorité au sujet si nécessaire
            if priority == "high":
                subject = f"[URGENT] {subject}"

            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(
                    settings, "DEFAULT_FROM_EMAIL", "noreply@elearning.com"
                ),
                recipient_list=self.admin_emails,
                fail_silently=False,
            )

            logger.info(f"Email envoyé à {len(self.admin_emails)} administrateurs")

        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")

    def _send_webhook_notification(self, title: str, message: str, status: str):
        """
        Envoie une notification via webhook (Slack, Discord, etc.)

        Args:
            title: Titre de la notification
            message: Message complet
            status: Statut (success, error, warning, info)
        """
        try:
            webhook_urls = getattr(settings, "NOTIFICATION_WEBHOOKS", {})

            if not webhook_urls:
                return

            # Préparer le payload selon le type de webhook
            for webhook_type, url in webhook_urls.items():
                if webhook_type == "slack":
                    self._send_slack_notification(url, title, message, status)
                elif webhook_type == "discord":
                    self._send_discord_notification(url, title, message, status)
                elif webhook_type == "teams":
                    self._send_teams_notification(url, title, message, status)
                else:
                    self._send_generic_webhook(url, title, message, status)

        except Exception as e:
            logger.error(f"Erreur envoi webhook: {e}")

    def _send_slack_notification(
        self, webhook_url: str, title: str, message: str, status: str
    ):
        """Envoie une notification Slack"""
        import requests

        # Couleurs selon le statut
        color_map = {
            "success": "good",
            "error": "danger",
            "warning": "warning",
            "info": "#36a64f",
        }

        payload = {
            "attachments": [
                {
                    "color": color_map.get(status, "#36a64f"),
                    "title": title,
                    "text": message,
                    "footer": "E-Learning Platform",
                    "ts": int(datetime.now().timestamp()),
                }
            ]
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

    def _send_discord_notification(
        self, webhook_url: str, title: str, message: str, status: str
    ):
        """Envoie une notification Discord"""
        import requests

        # Couleurs selon le statut (format décimal)
        color_map = {
            "success": 0x28A745,  # Vert
            "error": 0xDC3545,  # Rouge
            "warning": 0xFFC107,  # Jaune
            "info": 0x17A2B8,  # Bleu
        }

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": color_map.get(status, 0x17A2B8),
                    "footer": {"text": "E-Learning Platform"},
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

    def _send_teams_notification(
        self, webhook_url: str, title: str, message: str, status: str
    ):
        """Envoie une notification Microsoft Teams"""
        import requests

        # Couleurs selon le statut
        color_map = {
            "success": "28a745",
            "error": "dc3545",
            "warning": "ffc107",
            "info": "17a2b8",
        }

        payload = {
            "@type": "MessageCard",
            "@context": "https://schema.org/extensions",
            "summary": title,
            "themeColor": color_map.get(status, "17a2b8"),
            "sections": [
                {
                    "activityTitle": title,
                    "activitySubtitle": "E-Learning Platform",
                    "text": message,
                    "facts": [
                        {"name": "Status", "value": status.upper()},
                        {
                            "name": "Time",
                            "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        },
                    ],
                }
            ],
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

    def _send_generic_webhook(
        self, webhook_url: str, title: str, message: str, status: str
    ):
        """Envoie une notification webhook générique"""
        import requests

        payload = {
            "title": title,
            "message": message,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "source": "E-Learning Platform",
        }

        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

    def send_daily_summary(self):
        """Envoie un résumé quotidien des importations"""
        try:
            from courses.models import ImportLog
            from django.utils import timezone

            # Statistiques des dernières 24h
            yesterday = timezone.now() - timezone.timedelta(days=1)
            recent_imports = ImportLog.objects.filter(started_at__gte=yesterday)

            if not recent_imports.exists():
                return

            # Calculer les statistiques
            total_files = recent_imports.count()
            successful = recent_imports.filter(status="completed").count()
            failed = recent_imports.filter(status="error").count()
            total_courses_imported = sum(log.imported_count for log in recent_imports)
            total_courses_updated = sum(log.updated_count for log in recent_imports)

            subject = f"📊 Résumé quotidien - Importations de cours"

            message = f"""
📊 Résumé Quotidien des Importations

Période: {yesterday.strftime('%Y-%m-%d')} - {timezone.now().strftime('%Y-%m-%d')}

📈 Statistiques:
• Fichiers traités: {total_files}
• Succès: {successful} ({successful/total_files*100:.1f}%)
• Échecs: {failed} ({failed/total_files*100:.1f}%)

📚 Cours:
• Nouveaux cours: {total_courses_imported}
• Cours mis à jour: {total_courses_updated}
• Total traité: {total_courses_imported + total_courses_updated}

🔍 Détails des échecs:
{chr(10).join(f"  - {log.filename}: {log.error_message[:100]}..." 
              for log in recent_imports.filter(status='error')[:5])}

---
E-Learning Platform - Daily Report
            """.strip()

            # Envoyer uniquement par email
            if self.email_enabled and self.admin_emails:
                self._send_email(subject, message)

            logger.info("Résumé quotidien envoyé")

        except Exception as e:
            logger.error(f"Erreur envoi résumé quotidien: {e}")

    def test_notifications(self) -> Dict[str, Any]:
        """
        Test des notifications

        Returns:
            Résultats des tests
        """
        results = {"email": False, "webhooks": {}, "errors": []}

        try:
            # Test email
            if self.email_enabled and self.admin_emails:
                try:
                    self._send_email(
                        "🧪 Test de notification",
                        "Ceci est un test des notifications email du système d'importation de cours.",
                        priority="normal",
                    )
                    results["email"] = True
                except Exception as e:
                    results["errors"].append(f"Email: {e}")

            # Test webhooks
            webhook_urls = getattr(settings, "NOTIFICATION_WEBHOOKS", {})
            for webhook_type, url in webhook_urls.items():
                try:
                    self._send_webhook_notification(
                        "🧪 Test de notification",
                        "Ceci est un test des notifications webhook du système d'importation de cours.",
                        "info",
                    )
                    results["webhooks"][webhook_type] = True
                except Exception as e:
                    results["webhooks"][webhook_type] = False
                    results["errors"].append(f"{webhook_type}: {e}")

            return results

        except Exception as e:
            results["errors"].append(f"Test général: {e}")
            return results
