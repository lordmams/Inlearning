from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from datetime import datetime

from .forms import CourseImportForm
from services.course_importer import CourseImporter
from courses.models import ImportLog

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class CourseImportAPIView(View):
    """API pour l'importation de cours depuis le consumer"""

    def post(self, request):
        """Traite l'importation d'un fichier de cours"""
        try:
            # Vérifier l'authentification (optionnel)
            auth_header = request.META.get("HTTP_AUTHORIZATION", "")
            if auth_header and not self._validate_token(auth_header):
                return JsonResponse({"error": "Token invalide"}, status=401)

            # Traiter les données
            if not request.FILES.get("file"):
                return JsonResponse({"error": "Aucun fichier fourni"}, status=400)

            file = request.FILES["file"]
            format_type = request.POST.get("format_type", "json")
            update_existing = (
                request.POST.get("update_existing", "true").lower() == "true"
            )
            dry_run = request.POST.get("dry_run", "false").lower() == "true"

            # Créer le formulaire pour validation
            form_data = {
                "format_type": format_type,
                "update_existing": update_existing,
                "dry_run": dry_run,
            }
            form_files = {"file": file}

            form = CourseImportForm(form_data, form_files)

            if not form.is_valid():
                return JsonResponse(
                    {"error": "Données invalides", "details": form.errors}, status=400
                )

            # Traiter l'importation
            importer = CourseImporter()
            result = importer.import_from_file(
                file=file,
                format_type=format_type,
                update_existing=update_existing,
                dry_run=dry_run,
            )

            logger.info(
                f"Import API: {file.name} - {result.get('imported_count', 0)} cours importés"
            )

            return JsonResponse(result)

        except Exception as e:
            logger.error(f"Erreur API import: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "error": str(e),
                    "imported_count": 0,
                    "updated_count": 0,
                    "errors": [str(e)],
                },
                status=500,
            )

    def _validate_token(self, auth_header: str) -> bool:
        """Valide le token d'authentification (simple pour l'exemple)"""
        # Format: "Bearer <token>"
        if not auth_header.startswith("Bearer "):
            return False

        token = auth_header[7:]  # Enlever "Bearer "

        # Ici vous pouvez implémenter votre logique de validation
        # Pour l'exemple, on accepte n'importe quel token non vide
        return len(token) > 0


@method_decorator(csrf_exempt, name="dispatch")
class ImportLogAPIView(View):
    """API pour recevoir les logs du consumer"""

    def post(self, request):
        """Crée un log d'importation"""
        try:
            data = json.loads(request.body)

            # Créer le log
            import_log = ImportLog.objects.create(
                filename=data.get("filename", ""),
                file_path=data.get("file_path", ""),
                status=data.get("status", "pending"),
                started_at=datetime.fromisoformat(
                    data.get("started_at", datetime.now().isoformat())
                ),
                completed_at=(
                    datetime.fromisoformat(data.get("completed_at"))
                    if data.get("completed_at")
                    else None
                ),
                imported_count=data.get("imported_count", 0),
                updated_count=data.get("updated_count", 0),
                error_count=data.get("error_count", 0),
                error_message=data.get("error_message", ""),
                result_data=data.get("result_data"),
            )

            return JsonResponse({"success": True, "log_id": import_log.id}, status=201)

        except Exception as e:
            logger.error(f"Erreur création log: {e}")
            return JsonResponse({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class ConsumerStatusAPIView(View):
    """API pour recevoir les notifications de statut du consumer"""

    def post(self, request):
        """Reçoit les notifications de statut du consumer"""
        try:
            data = json.loads(request.body)

            status = data.get("status", "unknown")
            message = data.get("message", "")
            consumer_id = data.get("consumer_id", "unknown")

            logger.info(f"Consumer {consumer_id} status: {status} - {message}")

            # Ici vous pouvez stocker le statut en base ou déclencher des actions
            # Pour l'exemple, on log simplement

            return JsonResponse({"success": True})

        except Exception as e:
            logger.error(f"Erreur notification consumer: {e}")
            return JsonResponse({"error": str(e)}, status=500)


# Vues fonctionnelles pour compatibilité
@csrf_exempt
@require_http_methods(["POST"])
def course_import_api(request):
    """Vue fonctionnelle pour l'import de cours"""
    view = CourseImportAPIView()
    return view.post(request)


@csrf_exempt
@require_http_methods(["POST"])
def import_log_api(request):
    """Vue fonctionnelle pour les logs"""
    view = ImportLogAPIView()
    return view.post(request)


@csrf_exempt
@require_http_methods(["POST"])
def consumer_status_api(request):
    """Vue fonctionnelle pour le statut consumer"""
    view = ConsumerStatusAPIView()
    return view.post(request)


@staff_member_required
def consumer_health_check(request):
    """Health check du consumer via API"""
    try:
        import requests
        import os

        # Tester la connexion au consumer (si il expose une API)
        consumer_url = os.getenv("CONSUMER_URL", "http://flask_api:5000")

        try:
            response = requests.get(f"{consumer_url}/health", timeout=5)
            consumer_status = (
                response.json() if response.status_code == 200 else {"status": "error"}
            )
        except:
            consumer_status = {"status": "unreachable"}

        # Statistiques des répertoires (simulées pour l'exemple)
        ingest_stats = {"drop": 0, "processing": 0, "processed": 0, "error": 0}

        # Logs récents
        recent_logs = ImportLog.objects.all()[:10]
        logs_data = [
            {
                "filename": log.filename,
                "status": log.status,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "imported_count": log.imported_count,
                "error_message": log.error_message,
            }
            for log in recent_logs
        ]

        return JsonResponse(
            {
                "consumer_status": consumer_status,
                "ingest_stats": ingest_stats,
                "recent_logs": logs_data,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
