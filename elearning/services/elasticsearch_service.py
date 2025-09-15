import os
import requests
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class ElasticsearchService:
    def __init__(self):
        self.host = os.environ.get(
            "ELASTICSEARCH_HOST",
            "https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud",
        )
        self.index = os.environ.get("ELASTICSEARCH_INDEX", "inlearning-storage")
        self.api_key = os.environ.get("ELASTICSEARCH_API_KEY", "")

        self.headers = {
            "Authorization": f"ApiKey {self.api_key}",
            "Content-Type": "application/json",
        }

    def search_courses(
        self,
        query: str = "*",
        size: int = 100,
        from_: int = 0,
        category: str = None,
        level: str = None,
        sort_by: str = "relevance",
    ) -> Dict[str, Any]:
        """
        Recherche des cours dans Elasticsearch
        """
        try:
            # Construction de la requête
            search_query = {
                "size": size,
                "from": from_,
                "query": {"bool": {"must": []}},
                "sort": self._get_sort_config(sort_by),
            }

            # Requête de recherche textuelle
            if query and query != "*":
                search_query["query"]["bool"]["must"].append(
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "cours.titre^3",
                                "cours.description^2",
                                "cours.contenus.paragraphs",
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO",
                        }
                    }
                )
            else:
                search_query["query"]["bool"]["must"].append({"match_all": {}})

            # Filtres
            if category:
                search_query["query"]["bool"]["must"].append(
                    {"term": {"predictions.predicted_category.keyword": category}}
                )

            if level:
                search_query["query"]["bool"]["must"].append(
                    {"term": {"predictions.predicted_level.keyword": level}}
                )

            url = f"{self.host}/{self.index}/_search"
            response = requests.post(
                url, headers=self.headers, json=search_query, timeout=30
            )
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Erreur recherche Elasticsearch: {e}")
            return {"hits": {"hits": [], "total": {"value": 0}}}

    def get_course_by_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un cours par son ID
        """
        try:
            url = f"{self.host}/{self.index}/_doc/{course_id}"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                response.raise_for_status()

        except Exception as e:
            logger.error(f"Erreur récupération cours {course_id}: {e}")
            return None

    def get_all_courses(self, size: int = 1000) -> List[Dict[str, Any]]:
        """
        Récupère tous les cours (pour les statistiques)
        """
        try:
            search_query = {
                "size": size,
                "query": {"match_all": {}},
                "_source": [
                    "cours.titre",
                    "cours.description",
                    "cours.niveau",
                    "predictions.predicted_category",
                    "predictions.predicted_level",
                ],
            }

            url = f"{self.host}/{self.index}/_search"
            response = requests.post(
                url, headers=self.headers, json=search_query, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            return [hit["_source"] for hit in result["hits"]["hits"]]

        except Exception as e:
            logger.error(f"Erreur récupération tous les cours: {e}")
            return []

    def get_course_count(self) -> int:
        """
        Retourne le nombre total de cours
        """
        try:
            url = f"{self.host}/{self.index}/_count"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            result = response.json()
            return result.get("count", 0)

        except Exception as e:
            logger.error(f"Erreur comptage cours: {e}")
            return 0

    def get_categories_stats(self) -> List[Dict[str, Any]]:
        """
        Récupère les statistiques par catégorie
        """
        try:
            search_query = {
                "size": 0,
                "aggs": {
                    "categories": {
                        "terms": {
                            "field": "predictions.predicted_category.keyword",
                            "size": 20,
                        }
                    }
                },
            }

            url = f"{self.host}/{self.index}/_search"
            response = requests.post(
                url, headers=self.headers, json=search_query, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            buckets = (
                result.get("aggregations", {}).get("categories", {}).get("buckets", [])
            )

            return [
                {"name": bucket["key"], "enrollment_count": bucket["doc_count"]}
                for bucket in buckets
            ]

        except Exception as e:
            logger.error(f"Erreur statistiques catégories: {e}")
            return []

    def get_levels_stats(self) -> List[Dict[str, Any]]:
        """
        Récupère les statistiques par niveau
        """
        try:
            search_query = {
                "size": 0,
                "aggs": {
                    "levels": {
                        "terms": {
                            "field": "predictions.predicted_level.keyword",
                            "size": 10,
                        }
                    }
                },
            }

            url = f"{self.host}/{self.index}/_search"
            response = requests.post(
                url, headers=self.headers, json=search_query, timeout=30
            )
            response.raise_for_status()

            result = response.json()
            buckets = (
                result.get("aggregations", {}).get("levels", {}).get("buckets", [])
            )

            return [
                {
                    "difficulty": bucket["key"],
                    "course_count": bucket["doc_count"],
                    "avg_completion": 75,  # Valeur simulée pour le moment
                }
                for bucket in buckets
            ]

        except Exception as e:
            logger.error(f"Erreur statistiques niveaux: {e}")
            return []

    def _get_sort_config(self, sort_by: str) -> List[Dict]:
        """Configure le tri selon le paramètre demandé"""
        sort_configs = {
            "relevance": [
                {"_score": {"order": "desc"}},
                {"cours.titre.keyword": {"order": "asc"}},
            ],
            "title": [
                {"cours.titre.keyword": {"order": "asc"}},
                {"_score": {"order": "desc"}},
            ],
            "difficulty": [
                {"predictions.predicted_level.keyword": {"order": "asc"}},
                {"_score": {"order": "desc"}},
            ],
            "category": [
                {"predictions.predicted_category.keyword": {"order": "asc"}},
                {"cours.titre.keyword": {"order": "asc"}},
            ],
        }

        return sort_configs.get(sort_by, sort_configs["relevance"])

    def import_data(self, data: List[Dict] = None) -> Dict[str, Any]:
        """
        Importe des données dans Elasticsearch
        """
        try:
            if not data:
                # Si aucune donnée fournie, renvoyer un succès avec un message
                return {
                    "success": True,
                    "message": "Aucune donnée à importer",
                    "imported_count": 0,
                }

            imported_count = 0
            errors = []

            for item in data:
                try:
                    # Générer un ID unique si non fourni
                    doc_id = item.get("id", f"doc_{imported_count}")

                    # Supprimer l'ID du document pour éviter les conflits
                    doc_data = {k: v for k, v in item.items() if k != "id"}

                    # Indexer le document
                    url = f"{self.host}/{self.index}/_doc/{doc_id}"
                    response = requests.put(
                        url, headers=self.headers, json=doc_data, timeout=10
                    )

                    if response.status_code in [200, 201]:
                        imported_count += 1
                    else:
                        errors.append(
                            f"Erreur pour document {doc_id}: {response.status_code}"
                        )

                except Exception as e:
                    errors.append(f"Erreur lors de l'import d'un document: {str(e)}")

            return {
                "success": imported_count > 0,
                "message": f"Importé {imported_count} documents avec {len(errors)} erreurs",
                "imported_count": imported_count,
                "errors": errors[:10],  # Limiter à 10 erreurs max
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'import de données: {e}")
            return {
                "success": False,
                "message": f"Erreur lors de l'import: {str(e)}",
                "imported_count": 0,
                "errors": [str(e)],
            }


# Instance globale
elasticsearch_service = ElasticsearchService()
