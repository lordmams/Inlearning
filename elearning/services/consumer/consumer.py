import json
import logging
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import django
from django.conf import settings
from django.db import models
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Configuration Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning.settings")
django.setup()

from courses.models import Course, ImportLog

from ..course_importer import CourseImporter
from ..elastic_service import ElasticService
from ..notification_service import NotificationService

logger = logging.getLogger(__name__)


class CourseFileHandler(FileSystemEventHandler):
    """Gestionnaire d'événements pour les fichiers de cours"""

    def __init__(self, consumer):
        self.consumer = consumer
        super().__init__()

    def on_created(self, event):
        """Appelé quand un fichier est créé"""
        if not event.is_directory:
            self.consumer.process_file(event.src_path)

    def on_moved(self, event):
        """Appelé quand un fichier est déplacé"""
        if not event.is_directory:
            self.consumer.process_file(event.dest_path)


class CourseConsumer:
    """Consumer principal pour traiter les fichiers de cours"""

    def __init__(self):
        # Chemins de surveillance
        self.watch_dir = Path(settings.BASE_DIR.parent) / "ingest" / "drop"
        self.processing_dir = Path(settings.BASE_DIR.parent) / "ingest" / "processing"
        self.processed_dir = Path(settings.BASE_DIR.parent) / "ingest" / "processed"
        self.error_dir = Path(settings.BASE_DIR.parent) / "ingest" / "error"

        # Créer les répertoires s'ils n'existent pas
        self._create_directories()

        # Services
        self.importer = CourseImporter()
        self.elastic_service = ElasticService()
        self.notification_service = NotificationService()

        # Configuration
        self.supported_extensions = [".json", ".csv", ".xlsx"]
        self.max_file_size = 50 * 1024 * 1024  # 50MB

        # Observer pour surveiller les fichiers
        self.observer = Observer()
        self.observer.schedule(
            CourseFileHandler(self), str(self.watch_dir), recursive=False
        )

    def _create_directories(self):
        """Crée les répertoires nécessaires"""
        for directory in [
            self.watch_dir,
            self.processing_dir,
            self.processed_dir,
            self.error_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def start(self):
        """Démarre le consumer"""
        logger.info(f"Démarrage du consumer - Surveillance: {self.watch_dir}")

        # Traiter les fichiers existants
        self._process_existing_files()

        # Démarrer la surveillance
        self.observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Arrête le consumer"""
        logger.info("Arrêt du consumer")
        self.observer.stop()
        self.observer.join()

    def _process_existing_files(self):
        """Traite les fichiers déjà présents dans le répertoire"""
        for file_path in self.watch_dir.iterdir():
            if file_path.is_file():
                self.process_file(str(file_path))

    def process_file(self, file_path: str):
        """
        Traite un fichier de cours

        Args:
            file_path: Chemin vers le fichier à traiter
        """
        file_path = Path(file_path)

        # Créer un log d'importation
        import_log = ImportLog.objects.create(
            filename=file_path.name,
            file_path=str(file_path),
            status="processing",
            started_at=datetime.now(),
        )

        try:
            logger.info(f"Traitement du fichier: {file_path}")

            # Validation du fichier
            validation_result = self._validate_file(file_path)
            if not validation_result["valid"]:
                raise ValueError(validation_result["error"])

            # Déplacer vers processing
            processing_path = self._move_to_processing(file_path)

            # Traiter le fichier
            result = self._process_course_file(processing_path)

            # Mettre à jour le log
            import_log.status = "completed"
            import_log.completed_at = datetime.now()
            import_log.imported_count = result.get("imported_count", 0)
            import_log.updated_count = result.get("updated_count", 0)
            import_log.error_count = len(result.get("errors", []))
            import_log.result_data = result
            import_log.save()

            # Déplacer vers processed
            self._move_to_processed(processing_path)

            # Notification de succès
            self.notification_service.send_import_success_notification(
                filename=file_path.name, result=result
            )

            logger.info(f"Fichier traité avec succès: {file_path.name}")

        except Exception as e:
            logger.error(f"Erreur lors du traitement de {file_path}: {e}")

            # Mettre à jour le log d'erreur
            import_log.status = "error"
            import_log.completed_at = datetime.now()
            import_log.error_message = str(e)
            import_log.save()

            # Déplacer vers error
            try:
                processing_path = self.processing_dir / file_path.name
                if processing_path.exists():
                    self._move_to_error(processing_path)
                else:
                    self._move_to_error(file_path)
            except Exception as move_error:
                logger.error(f"Erreur lors du déplacement vers error: {move_error}")

            # Notification d'erreur
            self.notification_service.send_import_error_notification(
                filename=file_path.name, error=str(e)
            )

    def _validate_file(self, file_path: Path) -> Dict[str, Any]:
        """Valide un fichier avant traitement"""
        try:
            # Vérifier l'extension
            if file_path.suffix.lower() not in self.supported_extensions:
                return {
                    "valid": False,
                    "error": f"Extension non supportée: {file_path.suffix}",
                }

            # Vérifier la taille
            if file_path.stat().st_size > self.max_file_size:
                return {
                    "valid": False,
                    "error": f"Fichier trop volumineux: {file_path.stat().st_size} bytes",
                }

            # Vérifier que le fichier n'est pas vide
            if file_path.stat().st_size == 0:
                return {"valid": False, "error": "Fichier vide"}

            # Vérifier l'accès en lecture
            if not os.access(file_path, os.R_OK):
                return {"valid": False, "error": "Impossible de lire le fichier"}

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": f"Erreur de validation: {e}"}

    def _move_to_processing(self, file_path: Path) -> Path:
        """Déplace un fichier vers le répertoire de traitement"""
        processing_path = self.processing_dir / file_path.name

        # Si un fichier avec le même nom existe, ajouter un timestamp
        if processing_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name_parts = file_path.stem, timestamp, file_path.suffix
            processing_path = (
                self.processing_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
            )

        shutil.move(str(file_path), str(processing_path))
        return processing_path

    def _move_to_processed(self, file_path: Path) -> Path:
        """Déplace un fichier vers le répertoire des fichiers traités"""
        processed_path = self.processed_dir / file_path.name

        # Ajouter un timestamp pour éviter les conflits
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_parts = file_path.stem, timestamp, file_path.suffix
        processed_path = (
            self.processed_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
        )

        shutil.move(str(file_path), str(processed_path))
        return processed_path

    def _move_to_error(self, file_path: Path) -> Path:
        """Déplace un fichier vers le répertoire d'erreur"""
        error_path = self.error_dir / file_path.name

        # Ajouter un timestamp pour éviter les conflits
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_parts = file_path.stem, timestamp, file_path.suffix
        error_path = self.error_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"

        shutil.move(str(file_path), str(error_path))
        return error_path

    def _process_course_file(self, file_path: Path) -> Dict[str, Any]:
        """Traite un fichier de cours spécifique"""
        # Déterminer le format
        format_type = self._get_format_type(file_path)

        # Lire le fichier
        with open(file_path, "rb") as file:
            # Importer les cours
            result = self.importer.import_from_file(
                file=file, format_type=format_type, update_existing=True, dry_run=False
            )

        # Traiter les cours importés pour Elasticsearch
        if result["success"] and result["imported_count"] > 0:
            self._index_imported_courses(result)

        return result

    def _get_format_type(self, file_path: Path) -> str:
        """Détermine le type de format d'un fichier"""
        extension = file_path.suffix.lower()

        format_mapping = {".json": "json", ".csv": "csv", ".xlsx": "xlsx"}

        return format_mapping.get(extension, "json")

    def _index_imported_courses(self, import_result: Dict[str, Any]):
        """Indexe les cours importés dans Elasticsearch"""
        try:
            # Récupérer les cours récemment créés/modifiés
            recent_courses = Course.objects.filter(
                updated_at__gte=datetime.now().replace(second=0, microsecond=0)
            )

            # Indexer chaque cours
            for course in recent_courses:
                try:
                    self.elastic_service.index_course(course)
                    logger.info(f"Cours indexé dans Elasticsearch: {course.title}")
                except Exception as e:
                    logger.error(
                        f"Erreur indexation Elasticsearch pour {course.title}: {e}"
                    )

        except Exception as e:
            logger.error(f"Erreur lors de l'indexation Elasticsearch: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut du consumer"""
        return {
            "running": self.observer.is_alive(),
            "watch_directory": str(self.watch_dir),
            "processed_files": len(list(self.processed_dir.glob("*"))),
            "error_files": len(list(self.error_dir.glob("*"))),
            "pending_files": len(list(self.watch_dir.glob("*"))),
            "last_check": datetime.now().isoformat(),
        }


# ImportLog est maintenant défini dans courses/models.py


def main():
    """Point d'entrée principal du consumer"""
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("consumer.log"), logging.StreamHandler()],
    )

    # Créer et démarrer le consumer
    consumer = CourseConsumer()

    try:
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale du consumer: {e}")
    finally:
        consumer.stop()


if __name__ == "__main__":
    main()
