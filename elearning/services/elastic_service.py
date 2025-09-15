import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)


class ElasticService:
    """Service pour l'intégration avec Elasticsearch"""

    def __init__(self):
        self.enabled = getattr(settings, "ELASTICSEARCH_ENABLED", False)
        self.host = getattr(settings, "ELASTICSEARCH_HOST", "localhost:9200")
        self.index_name = getattr(settings, "ELASTICSEARCH_INDEX", "courses")
        self.api_key = getattr(settings, "ELASTICSEARCH_API_KEY", "")
        self.client = None

        if self.enabled:
            self._initialize_client()

    def _initialize_client(self):
        """Initialise le client Elasticsearch"""
        try:
            from elasticsearch import Elasticsearch

            # Configuration du client
            client_config = {"timeout": 30, "max_retries": 3, "retry_on_timeout": True}

            # Authentification par API Key
            if self.api_key:
                client_config["api_key"] = self.api_key
                logger.info("🔑 Authentification Elasticsearch via API Key")
            else:
                logger.warning("⚠️ Aucune API Key configurée pour Elasticsearch")

            # Configuration avec host URL
            self.client = Elasticsearch([self.host], **client_config)
            logger.info(f"🌐 Connexion Elasticsearch: {self.host}")

            # Tester la connexion
            if self.client.ping():
                logger.info("✅ Connexion Elasticsearch établie avec succès")
                self._ensure_index_exists()
            else:
                logger.error("❌ Impossible de se connecter à Elasticsearch")
                self.enabled = False

        except ImportError:
            logger.warning("elasticsearch-py non installé, fonctionnalité désactivée")
            self.enabled = False
        except Exception as e:
            logger.error(f"❌ Erreur initialisation Elasticsearch: {e}")
            self.enabled = False

    def _ensure_index_exists(self):
        """S'assure que l'index existe avec le bon mapping"""
        if not self.client:
            return

        try:
            if not self.client.indices.exists(index=self.index_name):
                # Créer l'index avec le mapping
                mapping = self._get_course_mapping()
                self.client.indices.create(
                    index=self.index_name,
                    body={
                        "mappings": mapping,
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0,
                            "analysis": {
                                "analyzer": {
                                    "course_analyzer": {
                                        "type": "custom",
                                        "tokenizer": "standard",
                                        "filter": ["lowercase", "stop", "snowball"],
                                    }
                                }
                            },
                        },
                    },
                )
                logger.info(f"Index Elasticsearch créé: {self.index_name}")

        except Exception as e:
            logger.error(f"Erreur création index Elasticsearch: {e}")

    def _get_course_mapping(self) -> Dict[str, Any]:
        """Définit le mapping pour les cours"""
        return {
            "properties": {
                "id": {"type": "integer"},
                "title": {
                    "type": "text",
                    "analyzer": "course_analyzer",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "description": {"type": "text", "analyzer": "course_analyzer"},
                "category": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "instructor": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "difficulty": {"type": "keyword"},
                "learning_mode": {"type": "keyword"},
                "duration": {"type": "integer"},
                "price": {"type": "float"},
                "is_free": {"type": "boolean"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
                "enrollment_count": {"type": "integer"},
                "completion_rate": {"type": "float"},
                "rating": {"type": "float"},
                "lessons": {
                    "type": "nested",
                    "properties": {
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "order": {"type": "integer"},
                        "video_url": {"type": "keyword"},
                    },
                },
                "tags": {"type": "keyword"},
                "suggest": {"type": "completion", "analyzer": "course_analyzer"},
            }
        }

    def index_course(self, course) -> bool:
        """
        Indexe un cours dans Elasticsearch

        Args:
            course: Instance du modèle Course

        Returns:
            True si l'indexation a réussi, False sinon
        """
        if not self.enabled or not self.client:
            return False

        try:
            # Préparer les données du cours
            doc = self._prepare_course_document(course)

            # Indexer le document
            response = self.client.index(index=self.index_name, id=course.id, body=doc)

            logger.info(f"Cours indexé: {course.title} (ID: {course.id})")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de l'indexation du cours {course.id}: {str(e)}")
            return False

    def index_course_json(self, course_data: Dict[str, Any]) -> bool:
        """
        Indexe un cours directement depuis des données JSON vers Elasticsearch

        Args:
            course_data: Dictionnaire contenant les données du cours au format JSON

        Returns:
            True si l'indexation a réussi, False sinon
        """
        if not self.enabled or not self.client:
            logger.warning("❌ Elasticsearch non activé ou client non initialisé")
            return False

        try:
            # Valider la structure de base
            if not isinstance(course_data, dict) or "cours" not in course_data:
                logger.error("❌ Structure de données invalide pour l'indexation")
                return False

            cours = course_data["cours"]
            course_id = cours.get("id")

            if not course_id:
                logger.error("❌ ID du cours manquant pour l'indexation")
                return False

            # Préparer le document pour Elasticsearch
            doc = {
                "url": course_data.get("url", ""),
                "cours": cours,
                "indexed_at": datetime.utcnow().isoformat(),
                "source": "direct_import",
            }

            # Indexer le document
            response = self.client.index(index=self.index_name, id=course_id, body=doc)

            if response.get("result") in ["created", "updated"]:
                logger.info(
                    f"✅ Cours '{cours.get('titre', 'Sans titre')}' indexé avec succès (ID: {course_id})"
                )
                return True
            else:
                logger.error(
                    f"❌ Échec de l'indexation du cours {course_id}: {response}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'indexation: {str(e)}")
            return False

    def _prepare_course_document(self, course) -> Dict[str, Any]:
        """Prépare le document Elasticsearch pour un cours"""
        # Données de base
        doc = {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "category": course.category.name if course.category else None,
            "instructor": course.instructor,
            "difficulty": course.difficulty,
            "learning_mode": course.learning_mode,
            "duration": course.duration,
            "price": float(course.price),
            "is_free": course.is_free,
            "created_at": course.created_at.isoformat() if course.created_at else None,
            "updated_at": course.updated_at.isoformat() if course.updated_at else None,
        }

        # Ajouter les leçons
        lessons = []
        for lesson in course.lessons.all():
            lessons.append(
                {
                    "title": lesson.title,
                    "content": lesson.content[:500],  # Limiter le contenu
                    "order": lesson.order,
                    "video_url": lesson.video_url or "",
                }
            )
        doc["lessons"] = lessons

        # Calculer les métriques
        enrollments = course.enrollments.all()
        doc["enrollment_count"] = enrollments.count()

        if enrollments.exists():
            completed = enrollments.filter(completed=True).count()
            doc["completion_rate"] = completed / enrollments.count() * 100
        else:
            doc["completion_rate"] = 0

        # Rating (à implémenter selon votre système)
        doc["rating"] = 4.0  # Valeur par défaut

        # Tags (basés sur le titre et la catégorie)
        tags = []
        if course.category:
            tags.append(course.category.name.lower())
        tags.extend(course.title.lower().split()[:5])  # Premiers mots du titre
        doc["tags"] = list(set(tags))

        # Suggestions pour l'autocomplétion
        doc["suggest"] = {
            "input": [course.title] + tags,
            "weight": doc["enrollment_count"] + 1,
        }

        return doc

    def search_courses(
        self, query: str, filters: Dict[str, Any] = None, size: int = 20, from_: int = 0
    ) -> Dict[str, Any]:
        """
        Recherche des cours dans Elasticsearch

        Args:
            query: Texte de recherche
            filters: Filtres à appliquer
            size: Nombre de résultats à retourner
            from_: Offset pour la pagination

        Returns:
            Dictionnaire avec les résultats de recherche
        """
        if not self.enabled or not self.client:
            return {"hits": {"hits": [], "total": {"value": 0}}}

        try:
            # Construire la requête
            search_body = self._build_search_query(query, filters)

            # Exécuter la recherche
            response = self.client.search(
                index=self.index_name, body=search_body, size=size, from_=from_
            )

            return response

        except Exception as e:
            logger.error(f"Erreur recherche Elasticsearch: {e}")
            return {"hits": {"hits": [], "total": {"value": 0}}}

    def _build_search_query(
        self, query: str, filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Construit la requête de recherche Elasticsearch"""
        search_body = {
            "query": {"bool": {"must": [], "filter": []}},
            "sort": [
                {"_score": {"order": "desc"}},
                {"enrollment_count": {"order": "desc"}},
            ],
            "highlight": {"fields": {"title": {}, "description": {}}},
        }

        # Requête de recherche textuelle
        if query:
            search_body["query"]["bool"]["must"].append(
                {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^3",
                            "description^2",
                            "instructor",
                            "category",
                            "lessons.title",
                            "lessons.content",
                        ],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                }
            )
        else:
            search_body["query"]["bool"]["must"].append({"match_all": {}})

        # Appliquer les filtres
        if filters:
            if filters.get("category"):
                search_body["query"]["bool"]["filter"].append(
                    {"term": {"category.keyword": filters["category"]}}
                )

            if filters.get("difficulty"):
                search_body["query"]["bool"]["filter"].append(
                    {"term": {"difficulty": filters["difficulty"]}}
                )

            if filters.get("learning_mode"):
                search_body["query"]["bool"]["filter"].append(
                    {"term": {"learning_mode": filters["learning_mode"]}}
                )

            if filters.get("is_free") is not None:
                search_body["query"]["bool"]["filter"].append(
                    {"term": {"is_free": filters["is_free"]}}
                )

            if (
                filters.get("min_price") is not None
                or filters.get("max_price") is not None
            ):
                price_range = {}
                if filters.get("min_price") is not None:
                    price_range["gte"] = filters["min_price"]
                if filters.get("max_price") is not None:
                    price_range["lte"] = filters["max_price"]

                search_body["query"]["bool"]["filter"].append(
                    {"range": {"price": price_range}}
                )

        return search_body

    def get_suggestions(self, text: str, size: int = 5) -> List[str]:
        """
        Obtient des suggestions d'autocomplétion

        Args:
            text: Texte pour l'autocomplétion
            size: Nombre de suggestions

        Returns:
            Liste des suggestions
        """
        if not self.enabled or not self.client:
            return []

        try:
            response = self.client.search(
                index=self.index_name,
                body={
                    "suggest": {
                        "course_suggest": {
                            "prefix": text,
                            "completion": {"field": "suggest", "size": size},
                        }
                    }
                },
            )

            suggestions = []
            for option in response["suggest"]["course_suggest"][0]["options"]:
                suggestions.append(option["text"])

            return suggestions

        except Exception as e:
            logger.error(f"Erreur suggestions Elasticsearch: {e}")
            return []

    def delete_course(self, course_id: int) -> bool:
        """
        Supprime un cours de l'index Elasticsearch

        Args:
            course_id: ID du cours à supprimer

        Returns:
            True si la suppression a réussi, False sinon
        """
        if not self.enabled or not self.client:
            return False

        try:
            response = self.client.delete(
                index=self.index_name,
                id=course_id,
                ignore=[404],  # Ignorer si le document n'existe pas
            )

            logger.info(f"Cours supprimé de l'index: {course_id}")
            return True

        except Exception as e:
            logger.error(f"Erreur suppression cours {course_id}: {e}")
            return False

    def bulk_index_courses(self, courses: List) -> Dict[str, int]:
        """
        Indexe plusieurs cours en lot

        Args:
            courses: Liste des cours à indexer

        Returns:
            Dictionnaire avec les statistiques d'indexation
        """
        if not self.enabled or not self.client:
            return {"indexed": 0, "errors": 0}

        try:
            from elasticsearch.helpers import bulk

            # Préparer les documents
            docs = []
            for course in courses:
                doc = self._prepare_course_document(course)
                docs.append(
                    {"_index": self.index_name, "_id": course.id, "_source": doc}
                )

            # Indexation en lot
            success, failed = bulk(self.client, docs, stats_only=True)

            logger.info(f"Indexation en lot: {success} réussies, {failed} échouées")
            return {"indexed": success, "errors": failed}

        except Exception as e:
            logger.error(f"Erreur indexation en lot: {e}")
            return {"indexed": 0, "errors": len(courses)}

    def get_analytics(self) -> Dict[str, Any]:
        """
        Obtient des analytics depuis Elasticsearch

        Returns:
            Dictionnaire avec les analytics
        """
        if not self.enabled or not self.client:
            return {}

        try:
            # Requête d'agrégation
            response = self.client.search(
                index=self.index_name,
                body={
                    "size": 0,
                    "aggs": {
                        "categories": {"terms": {"field": "category.keyword"}},
                        "difficulties": {"terms": {"field": "difficulty"}},
                        "learning_modes": {"terms": {"field": "learning_mode"}},
                        "price_stats": {"stats": {"field": "price"}},
                        "enrollment_stats": {"stats": {"field": "enrollment_count"}},
                    },
                },
            )

            return {
                "total_courses": response["hits"]["total"]["value"],
                "categories": [
                    {"name": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in response["aggregations"]["categories"]["buckets"]
                ],
                "difficulties": [
                    {"name": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in response["aggregations"]["difficulties"]["buckets"]
                ],
                "learning_modes": [
                    {"name": bucket["key"], "count": bucket["doc_count"]}
                    for bucket in response["aggregations"]["learning_modes"]["buckets"]
                ],
                "price_stats": response["aggregations"]["price_stats"],
                "enrollment_stats": response["aggregations"]["enrollment_stats"],
            }

        except Exception as e:
            logger.error(f"Erreur analytics Elasticsearch: {e}")
            return {}

    def health_check(self) -> Dict[str, Any]:
        """
        Vérifie l'état de santé d'Elasticsearch

        Returns:
            Dictionnaire avec l'état de santé
        """
        if not self.enabled:
            return {"status": "disabled", "message": "Elasticsearch désactivé"}

        if not self.client:
            return {"status": "error", "message": "Client Elasticsearch non initialisé"}

        try:
            # Vérifier la connexion
            if not self.client.ping():
                return {"status": "error", "message": "Impossible de se connecter"}

            # Vérifier l'état du cluster
            health = self.client.cluster.health()

            # Vérifier l'index
            index_stats = self.client.indices.stats(index=self.index_name)

            return {
                "status": "healthy",
                "cluster_status": health["status"],
                "cluster_name": health["cluster_name"],
                "number_of_nodes": health["number_of_nodes"],
                "index_exists": True,
                "document_count": index_stats["indices"][self.index_name]["total"][
                    "docs"
                ]["count"],
            }

        except Exception as e:
            return {"status": "error", "message": f"Erreur health check: {e}"}
