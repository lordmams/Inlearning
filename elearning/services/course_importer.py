import csv
import io
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

from courses.models import Category, Course, Lesson
from django.core.exceptions import ValidationError
from django.db import transaction

from .course_processor import CourseProcessor
from .elastic_service import ElasticService

logger = logging.getLogger(__name__)


class CourseImporter:
    """Service d'importation de cours depuis différents formats"""

    def __init__(self):
        self.processor = CourseProcessor()
        self.elastic_service = ElasticService()
        self.errors = []
        self.warnings = []
        self.imported_count = 0
        self.updated_count = 0
        self.skipped_count = 0

    def import_from_file(
        self,
        file,
        format_type: str,
        update_existing: bool = False,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Importe des cours depuis un fichier

        Args:
            file: Fichier uploadé
            format_type: Type de format (csv, json, xlsx)
            update_existing: Mettre à jour les cours existants
            dry_run: Mode test sans sauvegarde

        Returns:
            Dictionnaire avec les résultats d'importation
        """
        self._reset_counters()

        try:
            # Parser le fichier selon le format
            if format_type == "csv":
                courses_data = self._parse_csv(file)
            elif format_type == "json":
                courses_data = self._parse_json(file)
            elif format_type == "xlsx":
                courses_data = self._parse_xlsx(file)
            else:
                raise ValueError(f"Format non supporté: {format_type}")

            # Valider et traiter les données
            validated_courses = self._validate_courses_data(courses_data)

            # Importer les cours
            if not dry_run:
                self._import_courses(validated_courses, update_existing)
            else:
                self._simulate_import(validated_courses)

            return self._generate_import_report(dry_run)

        except Exception as e:
            logger.error(f"Erreur lors de l'importation: {e}")
            self.errors.append(f"Erreur générale: {e}")
            return self._generate_import_report(dry_run)

    def _parse_csv(self, file) -> List[Dict[str, Any]]:
        """Parse un fichier CSV"""
        content = file.read().decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(content))

        courses_data = []
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                course_data = self._normalize_csv_row(row)
                courses_data.append(course_data)
            except Exception as e:
                self.errors.append(f"Ligne {row_num}: {e}")

        return courses_data

    def _parse_json(self, file) -> List[Dict[str, Any]]:
        """Parse un fichier JSON"""
        content = file.read().decode("utf-8")
        data = json.loads(content)

        # Supporter différents formats JSON
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            if "courses" in data:
                return data["courses"]
            else:
                return [data]
        else:
            raise ValueError("Format JSON invalide")

    def _parse_xlsx(self, file) -> List[Dict[str, Any]]:
        """Parse un fichier Excel"""
        try:
            import pandas as pd

            df = pd.read_excel(file)
            return df.to_dict("records")
        except ImportError:
            raise ValueError("pandas requis pour les fichiers Excel")

    def _normalize_csv_row(self, row: Dict[str, str]) -> Dict[str, Any]:
        """Normalise une ligne CSV"""
        return {
            "title": row.get("title", "").strip(),
            "description": row.get("description", "").strip(),
            "category": row.get("category", "").strip(),
            "instructor": row.get("instructor", "").strip(),
            "duration": self._parse_int(row.get("duration", "0")),
            "difficulty": row.get("difficulty", "beginner").strip().lower(),
            "learning_mode": row.get("learning_mode", "text").strip().lower(),
            "price": self._parse_float(row.get("price", "0")),
            "is_free": self._parse_bool(row.get("is_free", "false")),
            "lessons": self._parse_lessons(row.get("lessons", "")),
            "tags": self._parse_tags(row.get("tags", "")),
        }

    def _parse_int(self, value: str) -> int:
        """Parse une valeur entière"""
        try:
            return int(float(value)) if value else 0
        except (ValueError, TypeError):
            return 0

    def _parse_float(self, value: str) -> float:
        """Parse une valeur décimale"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _parse_bool(self, value: str) -> bool:
        """Parse une valeur booléenne"""
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes", "oui", "vrai")

    def _parse_lessons(self, lessons_str: str) -> List[Dict[str, Any]]:
        """Parse les leçons depuis une chaîne"""
        if not lessons_str:
            return []

        try:
            # Essayer de parser comme JSON
            return json.loads(lessons_str)
        except json.JSONDecodeError:
            # Parser comme liste simple séparée par des virgules
            lessons = []
            for i, lesson_title in enumerate(lessons_str.split(";"), 1):
                if lesson_title.strip():
                    lessons.append(
                        {
                            "title": lesson_title.strip(),
                            "order": i,
                            "content": f"Contenu de la leçon: {lesson_title.strip()}",
                        }
                    )
            return lessons

    def _parse_tags(self, tags_str: str) -> List[str]:
        """Parse les tags depuis une chaîne"""
        if not tags_str:
            return []
        return [tag.strip() for tag in tags_str.split(",") if tag.strip()]

    def _validate_courses_data(
        self, courses_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Valide les données de cours"""
        validated_courses = []

        for i, course_data in enumerate(courses_data):
            try:
                # Validation des champs obligatoires
                if not course_data.get("title"):
                    self.errors.append(f"Cours {i+1}: Titre manquant")
                    continue

                if not course_data.get("description"):
                    self.warnings.append(f"Cours {i+1}: Description manquante")

                # Validation de la catégorie
                category_name = course_data.get("category", "Général")
                try:
                    category, created = Category.objects.get_or_create(
                        name=category_name,
                        defaults={"description": f"Catégorie {category_name}"},
                    )
                    course_data["category_obj"] = category
                except Exception as e:
                    self.errors.append(f"Cours {i+1}: Erreur catégorie - {e}")
                    continue

                # Validation de la difficulté
                if course_data.get("difficulty") not in [
                    "beginner",
                    "intermediate",
                    "advanced",
                ]:
                    course_data["difficulty"] = "beginner"
                    self.warnings.append(
                        f"Cours {i+1}: Difficulté invalide, définie à 'beginner'"
                    )

                # Validation du mode d'apprentissage
                if course_data.get("learning_mode") not in [
                    "video",
                    "text",
                    "practice",
                ]:
                    course_data["learning_mode"] = "text"
                    self.warnings.append(
                        f"Cours {i+1}: Mode d'apprentissage invalide, défini à 'text'"
                    )

                # Traitement avancé du cours
                processed_course = self.processor.process_course(course_data)
                validated_courses.append(processed_course)

            except Exception as e:
                self.errors.append(f"Cours {i+1}: Erreur de validation - {e}")

        return validated_courses

    def _import_courses(
        self, courses_data: List[Dict[str, Any]], update_existing: bool
    ):
        """Importe les cours dans la base de données"""
        with transaction.atomic():
            for course_data in courses_data:
                try:
                    self._import_single_course(course_data, update_existing)
                except Exception as e:
                    logger.error(
                        f"Erreur import cours '{course_data.get('title', 'Unknown')}': {e}"
                    )
                    self.errors.append(
                        f"Erreur import '{course_data.get('title', 'Unknown')}': {e}"
                    )

    def _import_single_course(self, course_data: Dict[str, Any], update_existing: bool):
        """Importe un seul cours"""
        title = course_data["title"]

        # Vérifier si le cours existe déjà
        existing_course = Course.objects.filter(title=title).first()

        if existing_course:
            if update_existing:
                # Mettre à jour le cours existant
                for field, value in course_data.items():
                    if field not in ["lessons", "category_obj"] and hasattr(
                        existing_course, field
                    ):
                        setattr(existing_course, field, value)

                if "category_obj" in course_data:
                    existing_course.category = course_data["category_obj"]

                existing_course.save()

                # Mettre à jour les leçons
                self._update_lessons(existing_course, course_data.get("lessons", []))

                # Indexer dans Elasticsearch
                self._index_course_in_elastic(existing_course)

                self.updated_count += 1
                logger.info(f"Cours mis à jour: {title}")
            else:
                self.skipped_count += 1
                logger.info(f"Cours ignoré (existe déjà): {title}")
        else:
            # Créer un nouveau cours
            course = Course.objects.create(
                title=course_data["title"],
                description=course_data["description"],
                category=course_data["category_obj"],
                instructor=course_data.get("instructor", "Instructeur par défaut"),
                duration=course_data.get("duration", 1),
                difficulty=course_data.get("difficulty", "beginner"),
                learning_mode=course_data.get("learning_mode", "text"),
                price=course_data.get("price", 0.0),
                is_free=course_data.get("is_free", True),
            )

            # Créer les leçons
            self._create_lessons(course, course_data.get("lessons", []))

            # Indexer dans Elasticsearch
            self._index_course_in_elastic(course)

            self.imported_count += 1
            logger.info(f"Nouveau cours créé: {title}")

    def _create_lessons(self, course: Course, lessons_data: List[Dict[str, Any]]):
        """Crée les leçons pour un cours"""
        for lesson_data in lessons_data:
            Lesson.objects.create(
                course=course,
                title=lesson_data.get("title", "Leçon sans titre"),
                content=lesson_data.get("content", ""),
                order=lesson_data.get("order", 1),
                video_url=lesson_data.get("video_url", ""),
            )

    def _update_lessons(self, course: Course, lessons_data: List[Dict[str, Any]]):
        """Met à jour les leçons d'un cours"""
        # Supprimer les anciennes leçons
        course.lessons.all().delete()

        # Créer les nouvelles leçons
        self._create_lessons(course, lessons_data)

    def _index_course_in_elastic(self, course: Course):
        """Indexe le cours dans Elasticsearch"""
        try:
            self.elastic_service.index_course(course)
        except Exception as e:
            logger.warning(
                f"Erreur indexation Elasticsearch pour le cours {course.title}: {e}"
            )

    def _simulate_import(self, courses_data: List[Dict[str, Any]]):
        """Simule l'importation pour le mode dry_run"""
        for course_data in courses_data:
            title = course_data["title"]
            existing_course = Course.objects.filter(title=title).first()

            if existing_course:
                self.updated_count += 1
            else:
                self.imported_count += 1

    def _reset_counters(self):
        """Remet à zéro les compteurs"""
        self.errors = []
        self.warnings = []
        self.imported_count = 0
        self.updated_count = 0
        self.skipped_count = 0

    def _generate_import_report(self, dry_run: bool) -> Dict[str, Any]:
        """Génère le rapport d'importation"""
        return {
            "success": len(self.errors) == 0,
            "dry_run": dry_run,
            "imported_count": self.imported_count,
            "updated_count": self.updated_count,
            "skipped_count": self.skipped_count,
            "total_processed": self.imported_count
            + self.updated_count
            + self.skipped_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": datetime.now().isoformat(),
        }

    def generate_template(self, template_type: str, format_type: str) -> str:
        """Génère un template d'importation"""
        if template_type == "basic":
            return self._generate_basic_template(format_type)
        elif template_type == "advanced":
            return self._generate_advanced_template(format_type)
        elif template_type == "bulk":
            return self._generate_bulk_template(format_type)
        else:
            raise ValueError(f"Type de template non supporté: {template_type}")

    def _generate_basic_template(self, format_type: str) -> str:
        """Génère un template basique"""
        if format_type == "csv":
            return (
                "title,description,category,instructor,duration,difficulty,learning_mode,price,is_free\n"
                + "Introduction à Python,Cours d'introduction au langage Python,Programmation,Jean Dupont,10,beginner,text,0,true\n"
                + "Python Avancé,Concepts avancés de Python,Programmation,Marie Martin,20,advanced,video,99.99,false"
            )

        elif format_type == "json":
            template_data = [
                {
                    "title": "Introduction à Python",
                    "description": "Cours d'introduction au langage Python",
                    "category": "Programmation",
                    "instructor": "Jean Dupont",
                    "duration": 10,
                    "difficulty": "beginner",
                    "learning_mode": "text",
                    "price": 0,
                    "is_free": True,
                },
                {
                    "title": "Python Avancé",
                    "description": "Concepts avancés de Python",
                    "category": "Programmation",
                    "instructor": "Marie Martin",
                    "duration": 20,
                    "difficulty": "advanced",
                    "learning_mode": "video",
                    "price": 99.99,
                    "is_free": False,
                },
            ]
            return json.dumps(template_data, indent=2, ensure_ascii=False)

    def _generate_advanced_template(self, format_type: str) -> str:
        """Génère un template avancé avec leçons"""
        if format_type == "json":
            template_data = [
                {
                    "title": "Django pour débutants",
                    "description": "Apprendre Django de zéro",
                    "category": "Web Development",
                    "instructor": "Pierre Durand",
                    "duration": 15,
                    "difficulty": "beginner",
                    "learning_mode": "practice",
                    "price": 49.99,
                    "is_free": False,
                    "lessons": [
                        {
                            "title": "Introduction à Django",
                            "content": "Qu'est-ce que Django et pourquoi l'utiliser",
                            "order": 1,
                            "video_url": "https://example.com/video1",
                        },
                        {
                            "title": "Premier projet",
                            "content": "Créer votre premier projet Django",
                            "order": 2,
                            "video_url": "https://example.com/video2",
                        },
                    ],
                    "tags": ["django", "python", "web", "backend"],
                }
            ]
            return json.dumps(template_data, indent=2, ensure_ascii=False)

        # Version CSV simplifiée pour le template avancé
        return (
            "title,description,category,instructor,duration,difficulty,learning_mode,price,is_free,lessons,tags\n"
            + "Django pour débutants,Apprendre Django de zéro,Web Development,Pierre Durand,15,beginner,practice,49.99,false,"
            + '"Introduction à Django;Premier projet","django,python,web,backend"'
        )

    def _generate_bulk_template(self, format_type: str) -> str:
        """Génère un template pour import en masse"""
        if format_type == "csv":
            headers = "title,description,category,instructor,duration,difficulty,learning_mode,price,is_free,lessons,tags"
            rows = []

            # Générer plusieurs exemples
            examples = [
                (
                    "HTML & CSS Basics",
                    "Apprendre les bases du HTML et CSS",
                    "Web Development",
                    "Alice Johnson",
                    8,
                    "beginner",
                    "text",
                    0,
                    True,
                    "Introduction HTML;Bases CSS;Responsive Design",
                    "html,css,responsive",
                ),
                (
                    "JavaScript Moderne",
                    "ES6+ et frameworks modernes",
                    "Web Development",
                    "Bob Smith",
                    12,
                    "intermediate",
                    "practice",
                    79.99,
                    False,
                    "ES6 Features;Async/Await;Modules",
                    "javascript,es6,async",
                ),
                (
                    "React Fundamentals",
                    "Créer des applications avec React",
                    "Web Development",
                    "Carol Brown",
                    16,
                    "intermediate",
                    "video",
                    129.99,
                    False,
                    "Components;State Management;Hooks",
                    "react,components,hooks",
                ),
                (
                    "Node.js Backend",
                    "Développement backend avec Node.js",
                    "Backend",
                    "David Wilson",
                    14,
                    "advanced",
                    "practice",
                    99.99,
                    False,
                    "Express Setup;Database Integration;API Design",
                    "nodejs,express,api",
                ),
                (
                    "Database Design",
                    "Conception de bases de données",
                    "Database",
                    "Eva Davis",
                    10,
                    "intermediate",
                    "text",
                    59.99,
                    False,
                    "SQL Basics;Normalization;Indexes",
                    "sql,database,design",
                ),
            ]

            for (
                title,
                desc,
                cat,
                instructor,
                duration,
                difficulty,
                mode,
                price,
                is_free,
                lessons,
                tags,
            ) in examples:
                rows.append(
                    f'"{title}","{desc}","{cat}","{instructor}",{duration},{difficulty},{mode},{price},{str(is_free).lower()},"{lessons}","{tags}"'
                )

            return headers + "\n" + "\n".join(rows)

        elif format_type == "json":
            # Template JSON avec plusieurs cours
            template_data = []
            examples = [
                ("HTML & CSS Basics", "Web Development", "Alice Johnson", "beginner"),
                ("JavaScript Moderne", "Web Development", "Bob Smith", "intermediate"),
                (
                    "React Fundamentals",
                    "Web Development",
                    "Carol Brown",
                    "intermediate",
                ),
                ("Node.js Backend", "Backend", "David Wilson", "advanced"),
                ("Database Design", "Database", "Eva Davis", "intermediate"),
            ]

            for title, category, instructor, difficulty in examples:
                template_data.append(
                    {
                        "title": title,
                        "description": f"Description détaillée du cours {title}",
                        "category": category,
                        "instructor": instructor,
                        "duration": 10,
                        "difficulty": difficulty,
                        "learning_mode": "text",
                        "price": 49.99,
                        "is_free": False,
                    }
                )

            return json.dumps(template_data, indent=2, ensure_ascii=False)
