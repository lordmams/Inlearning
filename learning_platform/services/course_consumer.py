import os
import json
import time
import logging
import shutil
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import uuid

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("/app/logs/consumer.log"), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


class CourseFileHandler(FileSystemEventHandler):
    """Gestionnaire d'événements pour les fichiers de cours"""

    def __init__(self, consumer):
        self.consumer = consumer
        super().__init__()

    def on_created(self, event):
        """Appelé quand un fichier est créé"""
        if not event.is_directory:
            file_path = Path(event.src_path)

            # Ignorer les fichiers de métadonnées et autres fichiers système
            if file_path.suffix.lower() in [".meta", ".tmp", ".temp", ".lock"]:
                logger.debug(f"Fichier ignoré (métadonnées): {event.src_path}")
                return

            # Ignorer les fichiers cachés
            if file_path.name.startswith("."):
                logger.debug(f"Fichier ignoré (caché): {event.src_path}")
                return

            logger.info(f"Nouveau fichier détecté: {event.src_path}")
            self.consumer.process_file(event.src_path)

    def on_moved(self, event):
        """Appelé quand un fichier est déplacé"""
        if not event.is_directory:
            file_path = Path(event.dest_path)

            # Ignorer les fichiers de métadonnées et autres fichiers système
            if file_path.suffix.lower() in [".meta", ".tmp", ".temp", ".lock"]:
                logger.debug(f"Fichier ignoré (métadonnées): {event.dest_path}")
                return

            # Ignorer les fichiers cachés
            if file_path.name.startswith("."):
                logger.debug(f"Fichier ignoré (caché): {event.dest_path}")
                return

            logger.info(f"Fichier déplacé: {event.dest_path}")
            self.consumer.process_file(event.dest_path)


class CourseConsumer:
    """Consumer principal pour traiter les fichiers de cours"""

    def __init__(self):
        # Configuration des chemins
        self.base_path = Path("/app/ingest")
        self.watch_dir = self.base_path / "drop"
        self.processing_dir = self.base_path / "processing"
        self.processed_dir = self.base_path / "processed"
        self.error_dir = self.base_path / "error"

        # Créer les répertoires s'ils n'existent pas
        self._create_directories()

        # Configuration API Django
        self.django_api_url = os.getenv("DJANGO_API_URL", "http://app:8000")
        self.api_token = os.getenv("API_TOKEN", "")

        # Configuration du consumer
        self.supported_extensions = [".json", ".csv", ".xlsx"]
        self.max_file_size = 50 * 1024 * 1024  # 50MB

        # Observer pour surveiller les fichiers
        self.observer = Observer()
        self.observer.schedule(
            CourseFileHandler(self), str(self.watch_dir), recursive=False
        )

        logger.info(f"Consumer initialisé - Surveillance: {self.watch_dir}")

    def _create_directories(self):
        """Crée les répertoires nécessaires"""
        for directory in [
            self.watch_dir,
            self.processing_dir,
            self.processed_dir,
            self.error_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Répertoire créé/vérifié: {directory}")

    def start(self):
        """Démarre le consumer"""
        logger.info(f"🚀 Démarrage du consumer - Surveillance: {self.watch_dir}")

        # Traiter les fichiers existants
        self._process_existing_files()

        # Démarrer la surveillance
        self.observer.start()

        # Notifier Django du démarrage
        self._notify_django("started", "Consumer démarré avec succès")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Arrête le consumer"""
        logger.info("⏹️ Arrêt du consumer")
        self.observer.stop()
        self.observer.join()

        # Notifier Django de l'arrêt
        self._notify_django("stopped", "Consumer arrêté")

    def _process_existing_files(self):
        """Traite les fichiers déjà présents dans le répertoire"""
        existing_files = list(self.watch_dir.glob("*"))
        if existing_files:
            logger.info(f"Traitement de {len(existing_files)} fichiers existants")
            for file_path in existing_files:
                if file_path.is_file():
                    self.process_file(str(file_path))

    def process_file(self, file_path: str):
        """
        Traite un fichier de cours

        Args:
            file_path: Chemin vers le fichier à traiter
        """
        file_path = Path(file_path)

        # Log de début de traitement
        log_data = {
            "filename": file_path.name,
            "file_path": str(file_path),
            "status": "processing",
            "started_at": datetime.now().isoformat(),
        }

        try:
            logger.info(f"📁 Traitement du fichier: {file_path}")

            # Validation du fichier
            validation_result = self._validate_file(file_path)
            if not validation_result["valid"]:
                raise ValueError(validation_result["error"])

            # Déplacer vers processing
            processing_path = self._move_to_processing(file_path)

            # Traiter le fichier via l'API Django
            result = self._send_to_learning_platform_api(processing_path)

            # Mettre à jour le log
            log_data.update(
                {
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "imported_count": result.get("imported_count", 0),
                    "updated_count": result.get("updated_count", 0),
                    "error_count": len(result.get("errors", [])),
                    "result_data": result,
                }
            )

            # Déplacer vers processed
            self._move_to_processed(processing_path)

            logger.info(f"✅ Fichier traité avec succès: {file_path.name}")

        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement de {file_path}: {e}")

            # Mettre à jour le log d'erreur
            log_data.update(
                {
                    "status": "error",
                    "completed_at": datetime.now().isoformat(),
                    "error_message": str(e),
                }
            )

            # Déplacer vers error
            try:
                processing_path = self.processing_dir / file_path.name
                if processing_path.exists():
                    self._move_to_error(processing_path)
                else:
                    self._move_to_error(file_path)
            except Exception as move_error:
                logger.error(f"Erreur lors du déplacement vers error: {move_error}")

        finally:
            # Envoyer le log à Django
            self._send_log_to_django(log_data)

    def _validate_file(self, file_path: Path) -> Dict[str, Any]:
        """Valide un fichier avant traitement"""
        try:
            # Vérifier l'extension
            if file_path.suffix.lower() not in self.supported_extensions:
                return {
                    "valid": False,
                    "error": f"Extension non supportée: {file_path.suffix}",
                }

            # Attendre que le fichier soit stable (pour éviter les problèmes de timing)
            import time

            max_wait = 5  # Attendre max 5 secondes
            wait_interval = 0.5  # Vérifier toutes les 0.5 secondes

            previous_size = -1
            for i in range(int(max_wait / wait_interval)):
                current_size = file_path.stat().st_size if file_path.exists() else 0

                if current_size == previous_size and current_size > 0:
                    # Le fichier est stable et non vide
                    break

                previous_size = current_size
                time.sleep(wait_interval)
                logger.debug(
                    f"Attente stabilité fichier {file_path.name}: {current_size} bytes"
                )

            # Vérifier la taille finale
            final_size = file_path.stat().st_size if file_path.exists() else 0

            if final_size > self.max_file_size:
                return {
                    "valid": False,
                    "error": f"Fichier trop volumineux: {final_size} bytes",
                }

            # Vérifier que le fichier n'est pas vide
            if final_size == 0:
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
        logger.info(f"Fichier déplacé vers processing: {processing_path}")
        return processing_path

    def _move_to_processed(self, file_path: Path) -> Path:
        """Déplace un fichier vers le répertoire des fichiers traités"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_parts = file_path.stem, timestamp, file_path.suffix
        processed_path = (
            self.processed_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
        )

        shutil.move(str(file_path), str(processed_path))
        logger.info(f"Fichier déplacé vers processed: {processed_path}")
        return processed_path

    def _move_to_error(self, file_path: Path) -> Path:
        """Déplace un fichier vers le répertoire d'erreur"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name_parts = file_path.stem, timestamp, file_path.suffix
        error_path = self.error_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"

        shutil.move(str(file_path), str(error_path))
        logger.info(f"Fichier déplacé vers error: {error_path}")
        return error_path

    def _send_to_learning_platform_api(self, file_path: Path) -> Dict[str, Any]:
        """Envoie les données directement au Learning Platform API pour traitement"""
        try:
            # Déterminer le format et parser le fichier
            format_type = self._get_format_type(file_path)
            courses_data = self._parse_file_data(file_path, format_type)

            if not courses_data:
                raise ValueError("Aucune donnée de cours trouvée dans le fichier")

            # Configuration de l'API Learning Platform
            learning_platform_url = os.getenv(
                "LEARNING_PLATFORM_URL", "http://flask_api:5000"
            )

            # Traiter selon le nombre de cours
            # Traitement par lots pour éviter les timeouts avec de gros volumes
            batch_size = 50  # Taille des lots
            all_results = []

            if len(courses_data) == 1:
                # Envoyer un cours unique
                logger.info(f"Envoi d'un cours unique au Learning Platform")
                response = requests.post(
                    f"{learning_platform_url}/process-single-course",
                    json=courses_data[0],
                    headers={"Content-Type": "application/json"},
                    timeout=300,
                )
                response.raise_for_status()
                result = response.json()
                all_results.append(result)

            else:
                # Traitement par lots
                total_batches = (len(courses_data) + batch_size - 1) // batch_size
                logger.info(
                    f"Envoi de {len(courses_data)} cours en {total_batches} lots au Learning Platform"
                )

                for i in range(0, len(courses_data), batch_size):
                    batch = courses_data[i : i + batch_size]
                    batch_num = i // batch_size + 1

                    logger.info(
                        f"Traitement lot {batch_num}/{total_batches} ({len(batch)} cours)"
                    )

                    response = requests.post(
                        f"{learning_platform_url}/process-courses-batch",
                        json=batch,
                        headers={"Content-Type": "application/json"},
                        timeout=300,
                    )
                    response.raise_for_status()
                    batch_result = response.json()

                    if isinstance(batch_result, list):
                        all_results.extend(batch_result)
                    else:
                        all_results.append(batch_result)

                    logger.info(
                        f"✅ Lot {batch_num}/{total_batches} traité avec succès"
                    )

                # Unifier les résultats
                result = all_results

            logger.info(
                f"Traitement terminé: {len(all_results) if isinstance(result, list) else 1} cours traités"
            )

            # Formatter la réponse pour le consumer
            return {
                "success": True,
                "imported_count": len(courses_data),
                "updated_count": 0,
                "errors": [],
                "learning_platform_response": result,
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur API Learning Platform: {e}")
            raise Exception(f"Erreur communication avec Learning Platform: {e}")
        except Exception as e:
            logger.error(f"Erreur traitement fichier: {e}")
            raise

    def _transform_course_format(self, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforme le format de cours pour l'API Flask"""
        try:
            # Si la structure a une clé 'cours', extraire les données
            if "cours" in course_data:
                cours_info = course_data["cours"]
                # Aplatir la structure
                # Utiliser l'ID existant s'il est présent, sinon générer un UUID unique
                existing_id = cours_info.get("id")
                if existing_id:
                    course_id = existing_id
                else:
                    course_id = str(uuid.uuid4())

                # Assurer que titre et description sont des strings
                titre_raw = cours_info.get("titre", "")
                description_raw = cours_info.get("description", "")

                titre_str = (
                    str(titre_raw)
                    if not isinstance(titre_raw, list)
                    else " ".join(str(x) for x in titre_raw)
                )
                description_str = (
                    str(description_raw)
                    if not isinstance(description_raw, list)
                    else " ".join(str(x) for x in description_raw)
                )

                transformed = {
                    "id": course_id,
                    "titre": titre_str,
                    "description": description_str,
                    "url": course_data.get("url", ""),
                    "lien": cours_info.get("lien", ""),
                    "contenus": cours_info.get("contenus", {}),
                    "categories": cours_info.get("categories", []),
                    "niveau": cours_info.get("niveau", ""),
                    "duree": cours_info.get("duree", ""),
                }
            else:
                # Si déjà au bon format, assurer la présence des champs requis
                # Utiliser l'ID existant s'il est présent, sinon générer un UUID unique
                existing_id = course_data.get("id")
                if existing_id:
                    course_id = existing_id
                else:
                    course_id = str(uuid.uuid4())

                # Assurer que titre et description sont des strings
                titre_raw = course_data.get("titre", "")
                description_raw = course_data.get("description", "")

                titre_str = (
                    str(titre_raw)
                    if not isinstance(titre_raw, list)
                    else " ".join(str(x) for x in titre_raw)
                )
                description_str = (
                    str(description_raw)
                    if not isinstance(description_raw, list)
                    else " ".join(str(x) for x in description_raw)
                )

                transformed = {
                    "id": course_id,
                    "titre": titre_str,
                    "description": description_str,
                    "url": course_data.get("url", ""),
                    "lien": course_data.get("lien", ""),
                    "contenus": course_data.get("contenus", {}),
                    "categories": course_data.get("categories", []),
                    "niveau": course_data.get("niveau", ""),
                    "duree": course_data.get("duree", ""),
                }

            return transformed

        except Exception as e:
            logger.error(f"Erreur transformation cours: {e}")
            return {}

    def _parse_file_data(
        self, file_path: Path, format_type: str
    ) -> List[Dict[str, Any]]:
        """Parse le fichier et retourne une liste de cours"""
        courses_data = []

        try:
            if format_type == "json":
                with open(file_path, "r", encoding="utf-8") as file:
                    data = json.load(file)

                    # Si c'est un tableau de cours
                    if isinstance(data, list):
                        courses_data = [
                            self._transform_course_format(course) for course in data
                        ]
                    # Si c'est un cours unique
                    elif isinstance(data, dict):
                        courses_data = [self._transform_course_format(data)]
                    else:
                        raise ValueError("Format JSON invalide")

            elif format_type in ["csv", "xlsx"]:
                # Pour CSV/XLSX, importer pandas ici
                try:
                    import pandas as pd

                    if format_type == "csv":
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path)

                    # Convertir chaque ligne en format de cours
                    for _, row in df.iterrows():
                        course_data = self._convert_row_to_course_format(row.to_dict())
                        if course_data:
                            courses_data.append(
                                self._transform_course_format(course_data)
                            )

                except ImportError:
                    raise Exception("pandas requis pour traiter les fichiers CSV/XLSX")

            logger.info(f"Parsed {len(courses_data)} cours depuis {file_path}")
            return courses_data

        except Exception as e:
            logger.error(f"Erreur parsing fichier {file_path}: {e}")
            raise

    def _convert_row_to_course_format(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convertit une ligne CSV/XLSX en format de cours pour l'API"""
        try:
            # Mapper les colonnes CSV vers le format attendu par l'API
            course_data = {
                "url": row_data.get("url", ""),
                "cours": {
                    "id": row_data.get("id", str(uuid.uuid4())),
                    "titre": row_data.get("titre", row_data.get("title", "")),
                    "description": row_data.get("description", ""),
                    "lien": row_data.get("lien", row_data.get("link", "")),
                    "contenus": {
                        "paragraphs": self._parse_list_field(
                            row_data.get("paragraphs", "")
                        ),
                        "lists": self._parse_nested_list_field(
                            row_data.get("lists", "")
                        ),
                        "examples": self._parse_list_field(
                            row_data.get("examples", "")
                        ),
                        "texte": row_data.get("texte", row_data.get("main_text", "")),
                        "lienVideo": row_data.get("video_link", ""),
                    },
                    "categories": self._parse_list_field(
                        row_data.get("categories", "")
                    ),
                    "niveau": row_data.get("niveau", row_data.get("level", "Débutant")),
                    "duree": row_data.get("duree", row_data.get("duration", "")),
                    "vecteur_embedding": [],
                },
            }

            return course_data

        except Exception as e:
            logger.error(f"Erreur conversion ligne: {e}")
            return None

    def _parse_list_field(self, field_value: str) -> List[str]:
        """Parse un champ de type liste depuis une chaîne"""
        if not field_value or (
            hasattr(field_value, "__iter__") and str(field_value) == "nan"
        ):
            return []

        try:
            # Essayer de parser en JSON d'abord
            if field_value.startswith("["):
                return json.loads(field_value)
            else:
                # Sinon, split par virgule
                return [
                    item.strip() for item in str(field_value).split(",") if item.strip()
                ]
        except:
            return [str(field_value)]

    def _parse_nested_list_field(self, field_value: str) -> List[List[str]]:
        """Parse un champ de type liste de listes depuis une chaîne"""
        if not field_value or (
            hasattr(field_value, "__iter__") and str(field_value) == "nan"
        ):
            return []

        try:
            # Essayer de parser en JSON d'abord
            if field_value.startswith("["):
                return json.loads(field_value)
            else:
                # Format simple: item1,item2;item3,item4
                outer_list = []
                for group in str(field_value).split(";"):
                    inner_list = [
                        item.strip() for item in group.split(",") if item.strip()
                    ]
                    if inner_list:
                        outer_list.append(inner_list)
                return outer_list
        except:
            return [[str(field_value)]]

    def _get_format_type(self, file_path: Path) -> str:
        """Détermine le type de format d'un fichier"""
        extension = file_path.suffix.lower()

        format_mapping = {".json": "json", ".csv": "csv", ".xlsx": "xlsx"}

        return format_mapping.get(extension, "json")

    def _get_content_type(self, format_type: str) -> str:
        """Retourne le content-type approprié"""
        content_types = {
            "json": "application/json",
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }

        return content_types.get(format_type, "application/octet-stream")

    def _send_log_to_django(self, log_data: Dict[str, Any]):
        """Envoie les logs à Django"""
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            response = requests.post(
                f"{self.django_api_url}/admin-dashboard/api/import-log/",
                json=log_data,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 201:
                logger.warning(f"Erreur envoi log à Django: {response.status_code}")

        except Exception as e:
            logger.error(f"Erreur envoi log: {e}")

    def _notify_django(self, status: str, message: str):
        """Notifie Django du statut du consumer"""
        try:
            notification_data = {
                "status": status,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "consumer_id": "course_consumer",
            }

            headers = {"Content-Type": "application/json"}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"

            response = requests.post(
                f"{self.django_api_url}/admin-dashboard/api/consumer-status/",
                json=notification_data,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                logger.info(f"Notification envoyée à Django: {status}")
            else:
                logger.warning(f"Erreur notification Django: {response.status_code}")

        except Exception as e:
            logger.error(f"Erreur notification: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Retourne le statut du consumer"""
        return {
            "running": self.observer.is_alive() if hasattr(self, "observer") else False,
            "watch_directory": str(self.watch_dir),
            "processed_files": len(list(self.processed_dir.glob("*"))),
            "error_files": len(list(self.error_dir.glob("*"))),
            "pending_files": len(list(self.watch_dir.glob("*"))),
            "last_check": datetime.now().isoformat(),
            "directories": {
                "drop": len(list(self.watch_dir.glob("*"))),
                "processing": len(list(self.processing_dir.glob("*"))),
                "processed": len(list(self.processed_dir.glob("*"))),
                "error": len(list(self.error_dir.glob("*"))),
            },
        }


def main():
    """Point d'entrée principal du consumer"""
    logger.info("🚀 Initialisation du consumer de cours...")

    # Attendre que Django soit prêt
    django_url = os.getenv("DJANGO_API_URL", "http://app:8000")
    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            response = requests.get(f"{django_url}/admin/", timeout=5)
            if response.status_code in [200, 302]:  # 302 = redirect vers login
                logger.info("✅ Django est prêt")
                break
        except requests.exceptions.RequestException:
            pass

        retry_count += 1
        logger.info(f"⏳ Attente de Django... ({retry_count}/{max_retries})")
        time.sleep(5)

    if retry_count >= max_retries:
        logger.error("❌ Impossible de se connecter à Django")
        return

    # Créer et démarrer le consumer
    consumer = CourseConsumer()

    try:
        consumer.start()
    except KeyboardInterrupt:
        logger.info("⏹️ Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur fatale du consumer: {e}")
    finally:
        consumer.stop()


if __name__ == "__main__":
    main()
