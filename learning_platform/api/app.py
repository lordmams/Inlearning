import json
import logging
import os
import pickle
import sys
import uuid
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import requests
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# Configuration des chemins pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services"
    )
)

# Imports du projet
try:
    from models.parcours_generation.filtering import filter_courses
    from models.parcours_generation.preprocessing import preprocess_courses
    from models.parcours_generation.recommender import recommend_courses
    from models.parcours_generation.sequencing import order_courses
except ImportError as e:
    print(f"Warning: Could not import course generation models: {e}")

    # Créer des fonctions mock pour le fallback
    def recommend_courses(user_profile, courses, top_k=10):
        return courses[:top_k] if courses else []

    def preprocess_courses(courses):
        return courses

    def filter_courses(courses, filters):
        return courses

    def order_courses(courses):
        return courses


try:
    from spark_service import spark_service
except ImportError as e:
    print(f"Warning: Could not import spark_service: {e}")

    # Créer un mock spark_service
    class MockSparkService:
        def is_cluster_available(self):
            return False

        def get_cluster_status(self):
            return {"status": "unavailable", "master_url": None}

        def submit_job(self, *args, **kwargs):
            return {"status": "error", "message": "Spark service not available"}

    spark_service = MockSparkService()

import anthropic
from dotenv import load_dotenv
from health import health_bp

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the course classifier and parcours generation modules
from models.course_pipeline.course_classifier import (CATEGORIES,
                                                      CourseClassifier)

app = Flask(__name__)
CORS(app)
app.register_blueprint(health_bp)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
logger.info(f"ANTHROPIC_API_KEY loaded: {'Yes' if ANTHROPIC_API_KEY else 'No'}")
logger.info(
    f"ANTHROPIC_API_KEY length: {len(ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else 0}"
)

# Configuration Elasticsearch pour envoi direct
ELASTICSEARCH_HOST = os.environ.get("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.environ.get("ELASTICSEARCH_INDEX", "courses")
ELASTICSEARCH_API_KEY = os.environ.get("ELASTICSEARCH_API_KEY", "")

# Compteur global pour les cours traités
processed_courses_count = 0


@app.route("/", methods=["GET"])
def api_documentation():
    """
    Route racine qui affiche la documentation HTML de l'API Flask
    """
    routes_info = {
        "api_name": "InLearning Platform API",
        "version": "1.0.0",
        "description": "API pour la plateforme d'apprentissage avec IA et Big Data",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "endpoints": {
            "/": {
                "methods": ["GET"],
                "description": "Documentation de l'API (cette page)",
                "parameters": "Aucun",
                "returns": "Page HTML avec documentation complète des routes",
            },
            "/health": {
                "methods": ["GET"],
                "description": "Vérification de l'état de santé de l'API",
                "parameters": "Aucun",
                "returns": "{'status': 'healthy', 'timestamp': '...'}",
            },
            "/status": {
                "methods": ["GET"],
                "description": "Statut détaillé de l'API et des services connectés",
                "parameters": "Aucun",
                "returns": "Informations sur l'état des modèles ML, Elasticsearch, Spark",
            },
            "/api/calculate-level": {
                "methods": ["POST"],
                "description": "Calcule le niveau d'un utilisateur basé sur son profil",
                "parameters": {
                    "user_data": {
                        "age": "int - Âge de l'utilisateur",
                        "gender": "str - Genre (M/F/O/P)",
                        "highest_academic_level": "str - Niveau académique",
                        "fields_of_study": "list - Domaines d'étude",
                        "professional_experience": "int - Années d'expérience",
                        "preferred_language": "str - Langue préférée",
                        "learning_mode": "str - Mode d'apprentissage",
                        "interests": "list - Centres d'intérêt",
                    }
                },
                "returns": "{'predicted_level': 'Débutant/Intermédiaire/Avancé', 'confidence': float}",
            },
            "/api/predict-category": {
                "methods": ["POST"],
                "description": "Prédit la catégorie d'un cours",
                "parameters": {
                    "titre": "str - Titre du cours",
                    "description": "str - Description du cours",
                },
                "returns": "{'predicted_category': 'str', 'confidence': float}",
            },
            "/api/predict-level": {
                "methods": ["POST"],
                "description": "Prédit le niveau de difficulté d'un cours",
                "parameters": {
                    "titre": "str - Titre du cours",
                    "description": "str - Description du cours",
                },
                "returns": "{'predicted_level': 'str', 'confidence': float}",
            },
            "/api/generate-learning-path": {
                "methods": ["POST"],
                "description": "Génère un parcours d'apprentissage personnalisé",
                "parameters": {
                    "user_profile": "object - Profil utilisateur complet",
                    "learning_objectives": "list - Objectifs d'apprentissage",
                    "preferences": "object - Préférences d'apprentissage",
                },
                "returns": "Parcours d'apprentissage avec cours recommandés et séquencement",
            },
            "/api/improve-learning-path": {
                "methods": ["POST"],
                "description": "Améliore un parcours existant avec l'IA",
                "parameters": {
                    "learning_path": "object - Parcours existant",
                    "feedback": "str - Retours utilisateur",
                },
                "returns": "Parcours amélioré avec suggestions IA",
            },
            "/api/claude-advice": {
                "methods": ["POST"],
                "description": "Obtient des conseils personnalisés via Claude AI",
                "parameters": {
                    "user_profile": "object - Profil utilisateur",
                    "current_courses": "list - Cours actuels",
                    "question": "str - Question spécifique (optionnel)",
                },
                "returns": "Conseils personnalisés et recommandations",
            },
            "/api/generate-quiz": {
                "methods": ["POST"],
                "description": "Génère un quiz adaptatif pour un cours",
                "parameters": {
                    "course_content": "str - Contenu du cours",
                    "difficulty_level": "str - Niveau de difficulté",
                    "num_questions": "int - Nombre de questions",
                },
                "returns": "Quiz généré avec questions et réponses",
            },
            "/process-single-course": {
                "methods": ["POST"],
                "description": "Traite un cours individuel (ML + Elasticsearch)",
                "parameters": {"course_data": "object - Données du cours à traiter"},
                "returns": "Cours traité avec catégorie, niveau et embedding",
            },
            "/process-courses-batch": {
                "methods": ["POST"],
                "description": "Traite plusieurs cours en lot",
                "parameters": {"courses": "list - Liste des cours à traiter"},
                "returns": "Résultats du traitement par lot",
            },
            "/process-courses-distributed": {
                "methods": ["POST"],
                "description": "Lance un traitement distribué avec Spark",
                "parameters": {
                    "input_path": "str - Chemin des données d'entrée",
                    "output_path": "str - Chemin de sortie",
                },
                "returns": "ID du job Spark lancé",
            },
            "/spark/job-status/<job_id>": {
                "methods": ["GET"],
                "description": "Vérifie le statut d'un job Spark",
                "parameters": "job_id dans l'URL",
                "returns": "Statut du job (RUNNING, COMPLETED, FAILED)",
            },
            "/spark/job-results/<job_id>": {
                "methods": ["GET"],
                "description": "Récupère les résultats d'un job Spark",
                "parameters": "job_id dans l'URL",
                "returns": "Résultats du traitement Spark",
            },
            "/stats/processed-courses": {
                "methods": ["GET"],
                "description": "Statistiques des cours traités",
                "parameters": "Aucun",
                "returns": "Nombre de cours traités et métriques",
            },
        },
        "models_loaded": {
            "student_level_model": "Modèle de prédiction du niveau utilisateur",
            "course_classifier": "Classificateur de catégories de cours",
            "course_level_model": "Modèle de prédiction du niveau de cours",
            "vectorizer": "Vectoriseur TF-IDF pour les embeddings",
        },
        "services_integration": {
            "elasticsearch": "Stockage et recherche de cours",
            "spark": "Traitement distribué des données",
            "claude_ai": "Conseils personnalisés et génération de contenu",
            "django": "Interface web et gestion utilisateurs",
        },
        "usage_examples": {
            "predict_user_level": 'curl -X POST http://localhost:5000/api/calculate-level -H \'Content-Type: application/json\' -d \'{"user_data": {"age": 25, "gender": "M", "highest_academic_level": "Master"}}\'',
            "process_course": 'curl -X POST http://localhost:5000/process-single-course -H \'Content-Type: application/json\' -d \'{"course_data": {"titre": "Python Basics", "description": "Learn Python programming"}}\'',
            "health_check": "curl http://localhost:5000/health",
        },
    }

    return render_template("api_documentation.html", **routes_info)
    """
    Route racine qui documente toutes les routes disponibles de l'API Flask
    """
    routes_info = {
        "api_name": "InLearning Platform API",
        "version": "1.0.0",
        "description": "API pour la plateforme d'apprentissage avec IA et Big Data",
        "endpoints": {
            "/": {
                "methods": ["GET"],
                "description": "Documentation de l'API (cette page)",
                "parameters": "Aucun",
                "returns": "Documentation complète des routes",
            },
            "/health": {
                "methods": ["GET"],
                "description": "Vérification de l'état de santé de l'API",
                "parameters": "Aucun",
                "returns": "{'status': 'healthy', 'timestamp': '...'}",
            },
            "/status": {
                "methods": ["GET"],
                "description": "Statut détaillé de l'API et des services connectés",
                "parameters": "Aucun",
                "returns": "Informations sur l'état des modèles ML, Elasticsearch, Spark",
            },
            "/api/calculate-level": {
                "methods": ["POST"],
                "description": "Calcule le niveau d'un utilisateur basé sur son profil",
                "parameters": {
                    "user_data": {
                        "age": "int - Âge de l'utilisateur",
                        "gender": "str - Genre (M/F/O/P)",
                        "highest_academic_level": "str - Niveau académique",
                        "fields_of_study": "list - Domaines d'étude",
                        "professional_experience": "int - Années d'expérience",
                        "preferred_language": "str - Langue préférée",
                        "learning_mode": "str - Mode d'apprentissage",
                        "interests": "list - Centres d'intérêt",
                    }
                },
                "returns": "{'predicted_level': 'Débutant/Intermédiaire/Avancé', 'confidence': float}",
            },
            "/api/predict-category": {
                "methods": ["POST"],
                "description": "Prédit la catégorie d'un cours",
                "parameters": {
                    "titre": "str - Titre du cours",
                    "description": "str - Description du cours",
                },
                "returns": "{'predicted_category': 'str', 'confidence': float}",
            },
            "/api/predict-level": {
                "methods": ["POST"],
                "description": "Prédit le niveau de difficulté d'un cours",
                "parameters": {
                    "titre": "str - Titre du cours",
                    "description": "str - Description du cours",
                },
                "returns": "{'predicted_level': 'str', 'confidence': float}",
            },
            "/api/generate-learning-path": {
                "methods": ["POST"],
                "description": "Génère un parcours d'apprentissage personnalisé",
                "parameters": {
                    "user_profile": "object - Profil utilisateur complet",
                    "learning_objectives": "list - Objectifs d'apprentissage",
                    "preferences": "object - Préférences d'apprentissage",
                },
                "returns": "Parcours d'apprentissage avec cours recommandés et séquencement",
            },
            "/api/improve-learning-path": {
                "methods": ["POST"],
                "description": "Améliore un parcours existant avec l'IA",
                "parameters": {
                    "learning_path": "object - Parcours existant",
                    "feedback": "str - Retours utilisateur",
                },
                "returns": "Parcours amélioré avec suggestions IA",
            },
            "/api/claude-advice": {
                "methods": ["POST"],
                "description": "Obtient des conseils personnalisés via Claude AI",
                "parameters": {
                    "user_profile": "object - Profil utilisateur",
                    "current_courses": "list - Cours actuels",
                    "question": "str - Question spécifique (optionnel)",
                },
                "returns": "Conseils personnalisés et recommandations",
            },
            "/api/generate-quiz": {
                "methods": ["POST"],
                "description": "Génère un quiz adaptatif pour un cours",
                "parameters": {
                    "course_content": "str - Contenu du cours",
                    "difficulty_level": "str - Niveau de difficulté",
                    "num_questions": "int - Nombre de questions",
                },
                "returns": "Quiz généré avec questions et réponses",
            },
            "/process-single-course": {
                "methods": ["POST"],
                "description": "Traite un cours individuel (ML + Elasticsearch)",
                "parameters": {"course_data": "object - Données du cours à traiter"},
                "returns": "Cours traité avec catégorie, niveau et embedding",
            },
            "/process-courses-batch": {
                "methods": ["POST"],
                "description": "Traite plusieurs cours en lot",
                "parameters": {"courses": "list - Liste des cours à traiter"},
                "returns": "Résultats du traitement par lot",
            },
            "/process-courses-distributed": {
                "methods": ["POST"],
                "description": "Lance un traitement distribué avec Spark",
                "parameters": {
                    "input_path": "str - Chemin des données d'entrée",
                    "output_path": "str - Chemin de sortie",
                },
                "returns": "ID du job Spark lancé",
            },
            "/spark/job-status/<job_id>": {
                "methods": ["GET"],
                "description": "Vérifie le statut d'un job Spark",
                "parameters": "job_id dans l'URL",
                "returns": "Statut du job (RUNNING, COMPLETED, FAILED)",
            },
            "/spark/job-results/<job_id>": {
                "methods": ["GET"],
                "description": "Récupère les résultats d'un job Spark",
                "parameters": "job_id dans l'URL",
                "returns": "Résultats du traitement Spark",
            },
            "/stats/processed-courses": {
                "methods": ["GET"],
                "description": "Statistiques des cours traités",
                "parameters": "Aucun",
                "returns": "Nombre de cours traités et métriques",
            },
        },
        "models_loaded": {
            "student_level_model": "Modèle de prédiction du niveau utilisateur",
            "course_classifier": "Classificateur de catégories de cours",
            "course_level_model": "Modèle de prédiction du niveau de cours",
            "vectorizer": "Vectoriseur TF-IDF pour les embeddings",
        },
        "services_integration": {
            "elasticsearch": "Stockage et recherche de cours",
            "spark": "Traitement distribué des données",
            "claude_ai": "Conseils personnalisés et génération de contenu",
            "django": "Interface web et gestion utilisateurs",
        },
        "usage_examples": {
            "predict_user_level": 'curl -X POST http://localhost:5000/api/calculate-level -H \'Content-Type: application/json\' -d \'{"user_data": {"age": 25, "gender": "M", "highest_academic_level": "Master"}}\'',
            "process_course": 'curl -X POST http://localhost:5000/process-single-course -H \'Content-Type: application/json\' -d \'{"course_data": {"titre": "Python Basics", "description": "Learn Python programming"}}\'',
            "health_check": "curl http://localhost:5000/health",
        },
    }

    return jsonify(routes_info)


def call_claude_api(prompt):
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY is not set")
        return "Clé API Claude manquante (ANTHROPIC_API_KEY non définie)."
    logger.info("Attempting to create Anthropic client...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        logger.info("Sending request to Claude API...")
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=512,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}],
        )
        logger.info("Received response from Claude API")
        # Pour la version anthropic>=0.7.7
        return (
            response.content[0].text if hasattr(response, "content") else str(response)
        )
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        return f"Erreur lors de l'appel à Claude : {e}"


def load_models():
    models_dir = Path(__file__).parent.parent / "models"
    logger.info(f"Loading models from: {models_dir}")

    try:
        # Load the student level model and its components
        student_level_model_path = models_dir / "student_level" / "best_model_rff.pkl"
        logger.info(f"Loading student level model from: {student_level_model_path}")
        model_details = joblib.load(student_level_model_path)

        # Extract components
        model = model_details["model"]
        scaler = model_details["scaler"]
        label_encoder = model_details["label_encoder"]
        feature_mappings = model_details["feature_mappings"]
        features = model_details["features"]

        logger.info("Student level model components loaded successfully")
        logger.info(f"Available features: {features}")
        logger.info(f"Feature mappings: {feature_mappings}")

    except Exception as e:
        logger.error(f"Error loading student level model: {str(e)}")
        raise

    try:
        # Load the course level model and vectorizer
        course_level_model_path = models_dir / "course_pipeline" / "level_model.joblib"
        vectorizer_path = models_dir / "course_pipeline" / "vectorizer.joblib"

        logger.info(f"Loading course level model from: {course_level_model_path}")
        course_level_model = joblib.load(course_level_model_path)
        logger.info(
            f"Course level model loaded successfully: {type(course_level_model)}"
        )

        logger.info(f"Loading vectorizer from: {vectorizer_path}")
        vectorizer = joblib.load(vectorizer_path)
        logger.info(f"Vectorizer loaded successfully: {type(vectorizer)}")

    except Exception as e:
        logger.error(f"Error loading course level model or vectorizer: {str(e)}")
        raise

    # Initialize the course classifier
    course_classifier = CourseClassifier(CATEGORIES)
    logger.info("Course classifier initialized successfully")

    return {
        "model": model,
        "scaler": scaler,
        "label_encoder": label_encoder,
        "feature_mappings": feature_mappings,
        "features": features,
        "course_level_model": course_level_model,
        "vectorizer": vectorizer,
        "course_classifier": course_classifier,
    }


# Load models at startup
logger.info("Starting to load models...")
models = load_models()
logger.info("All models loaded successfully")


def send_to_elasticsearch(course_data):
    """Envoie les données traitées directement à Elasticsearch"""
    try:
        # Préparer l'URL et les headers
        url = f"{ELASTICSEARCH_HOST}/{ELASTICSEARCH_INDEX}/_doc/{course_data['id']}"
        headers = {"Content-Type": "application/json"}

        if ELASTICSEARCH_API_KEY:
            headers["Authorization"] = f"ApiKey {ELASTICSEARCH_API_KEY}"

        # Formater pour Elasticsearch selon le template attendu
        es_document = {
            "url": course_data.get("url", ""),
            "cours": {
                "id": course_data["id"],
                "titre": course_data["titre"],
                "description": course_data["description"],
                "lien": course_data.get("lien", ""),
                "contenus": course_data.get("contenus", {}),
                "categories": (
                    course_data.get("categories", [])
                    if isinstance(course_data.get("categories"), list)
                    else [str(course_data.get("categories", ""))]
                ),
                "niveau": str(course_data.get("niveau", "")),
                "duree": course_data.get("duree", ""),
                "vecteur_embedding": course_data.get("vecteur_embedding", []),
            },
            "processed_at": course_data.get("processed_at"),
            "source": "learning_platform_pipeline",
            "predictions": {
                "predicted_category": course_data.get("predicted_category"),
                "category_confidence": course_data.get("category_confidence"),
                "predicted_level": course_data.get("predicted_level"),
                "level_confidence": course_data.get("level_confidence"),
            },
        }

        # Envoyer à Elasticsearch
        response = requests.put(url, json=es_document, headers=headers, timeout=30)

        if response.status_code in [200, 201]:
            logger.info(f"✅ Cours indexé dans Elasticsearch: {course_data['titre']}")
            return True
        else:
            logger.error(
                f"❌ Erreur Elasticsearch: {response.status_code} - {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"❌ Erreur envoi Elasticsearch: {e}")
        return False


def process_course_with_pipeline(course_data):
    """Traite un cours avec le pipeline de classification et prédiction de niveau"""
    try:
        logger.debug(f"Traitement cours ID: {course_data.get('id', 'unknown')}")
        logger.debug(
            f"Type titre: {type(course_data.get('titre', ''))}, Valeur: {course_data.get('titre', '')[:100]}..."
        )
        logger.debug(
            f"Type description: {type(course_data.get('description', ''))}, Valeur: {course_data.get('description', '')[:100]}..."
        )

        # Ajout debug pour voir TOUT le contenu du cours
        logger.debug(f"Contenu complet course_data keys: {list(course_data.keys())}")
        for key, value in course_data.items():
            logger.debug(f"  {key}: {type(value)} - {str(value)[:50]}...")
        # Utiliser le classificateur de catégories existant
        if "course_classifier" in models:
            title = (
                str(course_data.get("titre", "")) if course_data.get("titre") else ""
            )
            description = (
                str(course_data.get("description", ""))
                if course_data.get("description")
                else ""
            )

            # Classification de catégorie
            try:
                logger.debug(
                    f"Avant classification - title type: {type(title)}, description type: {type(description)}"
                )
                # Vérifier si la méthode predict_category existe, sinon utiliser classify_text
                if hasattr(models["course_classifier"], "predict_category"):
                    # Protection supplémentaire contre les listes
                    title_safe = (
                        str(title)
                        if not isinstance(title, list)
                        else " ".join(str(x) for x in title)
                    )
                    description_safe = (
                        str(description)
                        if not isinstance(description, list)
                        else " ".join(str(x) for x in description)
                    )
                    logger.debug(
                        f"Appel predict_category avec title_safe: {type(title_safe)}, description_safe: {type(description_safe)}"
                    )
                    predicted_category, confidence = models[
                        "course_classifier"
                    ].predict_category(title_safe, description_safe)
                elif hasattr(models["course_classifier"], "classify_text"):
                    # Protection supplémentaire contre les listes
                    try:
                        title_safe = (
                            str(title)
                            if not isinstance(title, list)
                            else " ".join(str(x) for x in title)
                        )
                        logger.debug(f"title_safe créé: {type(title_safe)}")
                    except Exception as e:
                        logger.error(f"Erreur création title_safe: {e}")
                        title_safe = "titre inconnu"

                    try:
                        description_safe = (
                            str(description)
                            if not isinstance(description, list)
                            else " ".join(str(x) for x in description)
                        )
                        logger.debug(f"description_safe créé: {type(description_safe)}")
                    except Exception as e:
                        logger.error(f"Erreur création description_safe: {e}")
                        description_safe = "description inconnue"

                    try:
                        combined_text = f"{title_safe} {description_safe}"
                        logger.debug(f"combined_text créé: {type(combined_text)}")
                    except Exception as e:
                        logger.error(f"Erreur création combined_text: {e}")
                        combined_text = "texte inconnu"

                    try:
                        logger.debug(
                            f"Appel classify_text avec combined_text type: {type(combined_text)}"
                        )
                        predicted_category, confidence = models[
                            "course_classifier"
                        ].classify_text(combined_text)
                        logger.debug(
                            f"classify_text réussi: {predicted_category}, {confidence}"
                        )
                    except Exception as e:
                        logger.error(f"Erreur dans classify_text: {e}")
                        predicted_category, confidence = "Général", 0.5
                else:
                    raise ValueError("Aucune méthode de classification disponible")
            except Exception as classify_error:
                logger.error(
                    f"Erreur classification pour cours {course_data.get('id', 'unknown')}: {classify_error}"
                )
                logger.error(
                    f"Title type: {type(title)}, Description type: {type(description)}"
                )
                predicted_category = "Général"
                confidence = 0.5
        else:
            # Fallback simple
            titre_safe = (
                str(course_data.get("titre", "")) if course_data.get("titre") else ""
            )
            predicted_category = (
                "Programmation"
                if any(
                    lang in titre_safe.lower()
                    for lang in ["python", "java", "javascript", "php"]
                )
                else "Général"
            )
            confidence = 0.7

        # Prédiction de niveau (simulation intelligente basée sur le contenu)
        titre = (
            str(course_data.get("titre", "")).lower()
            if course_data.get("titre")
            else ""
        )
        description = (
            str(course_data.get("description", "")).lower()
            if course_data.get("description")
            else ""
        )

        if any(
            word in titre or word in description
            for word in ["avancé", "expert", "maître", "advanced"]
        ):
            predicted_level = "Avancé"
            level_confidence = 0.8
        elif any(
            word in titre or word in description
            for word in ["intermédiaire", "intermediate"]
        ):
            predicted_level = "Intermédiaire"
            level_confidence = 0.7
        else:
            predicted_level = "Débutant"
            level_confidence = 0.6

        # Génération d'embedding simplifié (en production, utiliser un vrai modèle)
        try:
            titre_raw = course_data.get("titre", "")
            if isinstance(titre_raw, list):
                titre_str = " ".join(str(x) for x in titre_raw)
            else:
                titre_str = str(titre_raw) if titre_raw else ""
        except Exception as e:
            logger.error(f"Erreur traitement titre pour embedding: {e}")
            titre_str = "titre inconnu"

        try:
            description_raw = course_data.get("description", "")
            if isinstance(description_raw, list):
                description_str = " ".join(str(x) for x in description_raw)
            else:
                description_str = str(description_raw) if description_raw else ""
        except Exception as e:
            logger.error(f"Erreur traitement description pour embedding: {e}")
            description_str = "description inconnue"

        try:
            text_for_embedding = f"{titre_str} {description_str}".strip()
        except Exception as e:
            logger.error(f"Erreur création text_for_embedding: {e}")
            text_for_embedding = "cours général"

        # S'assurer qu'on a du texte pour l'embedding, sinon utiliser un texte par défaut
        if not text_for_embedding:
            text_for_embedding = "cours général"

        # Simulation d'embedding basé sur la longueur et les mots-clés (éviter les vecteurs zéro)
        import hashlib

        # Créer des hash différents pour chaque dimension
        embedding = []
        for i in range(384):
            hash_input = f"{text_for_embedding}_{i}"
            hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
            # Normaliser entre 0.1 et 1.0 pour éviter les zéros
            normalized_value = 0.1 + (hash_value % 90) / 100.0
            embedding.append(normalized_value)

        return {
            "predicted_category": predicted_category,
            "category_confidence": confidence,
            "predicted_level": predicted_level,
            "level_confidence": level_confidence,
            "vecteur_embedding": embedding,
        }

    except Exception as e:
        import traceback

        logger.error(f"Erreur traitement pipeline: {e}")
        logger.error(f"Traceback complet: {traceback.format_exc()}")
        return {
            "predicted_category": "Général",
            "category_confidence": 0.5,
            "predicted_level": "Débutant",
            "level_confidence": 0.5,
            "vecteur_embedding": [],
        }


@app.route("/api/calculate-level", methods=["POST"])
def calculate_user_level():
    try:
        data = request.get_json()
        user_data = data.get("user_data", {})
        logger.info(f"Received user data: {user_data}")

        # Log the available feature mappings
        logger.info(
            f"Available gender mappings: {models['feature_mappings']['gender']}"
        )
        logger.info(
            f"Available language mappings: {models['feature_mappings']['preferred_language']}"
        )
        logger.info(
            f"Available learning mode mappings: {models['feature_mappings']['learning_mode']}"
        )
        logger.info(
            f"Available academic level mappings: {models['feature_mappings']['highest_academic_level']}"
        )
        logger.info(
            f"Available field of study mappings: {models['feature_mappings']['fields_of_study']}"
        )

        # Safely get mapped values with defaults
        def get_mapped_value(mapping_dict, key, default_key):
            try:
                # First try to get the provided key
                if key in mapping_dict:
                    return mapping_dict[key]
                # If not found, use the first available key as default
                default_value = next(iter(mapping_dict.values()))
                logger.warning(
                    f"Key '{key}' not found in mappings. Using default value: {default_value}"
                )
                return default_value
            except Exception as e:
                logger.error(f"Error in get_mapped_value: {str(e)}")
                # Return the first available value as a last resort
                return next(iter(mapping_dict.values()))

        # Create input DataFrame with the correct features
        input_data = pd.DataFrame(
            {
                "age": [user_data.get("age", 0)],
                "gender": [
                    get_mapped_value(
                        models["feature_mappings"]["gender"],
                        user_data.get("gender", ""),
                        "",
                    )
                ],
                "preferred_language": [
                    get_mapped_value(
                        models["feature_mappings"]["preferred_language"],
                        user_data.get("preferred_language", ""),
                        "",
                    )
                ],
                "learning_mode": [
                    get_mapped_value(
                        models["feature_mappings"]["learning_mode"],
                        user_data.get("learning_mode", ""),
                        "",
                    )
                ],
                "highest_academic_level": [
                    get_mapped_value(
                        models["feature_mappings"]["highest_academic_level"],
                        user_data.get("highest_academic_level", ""),
                        "",
                    )
                ],
                "total_experience_years": [user_data.get("total_experience_years", 0)],
                "fields_of_study": [
                    get_mapped_value(
                        models["feature_mappings"]["fields_of_study"],
                        user_data.get("fields_of_study", ""),
                        "",
                    )
                ],
            }
        )

        logger.info(f"Input data: {input_data}")

        # Scale the features
        input_scaled = models["scaler"].transform(input_data[models["features"]])
        logger.info(f"Scaled input: {input_scaled}")

        # Make prediction
        prediction = models["model"].predict(input_scaled)
        prediction_label = models["label_encoder"].inverse_transform(prediction)[0]
        prediction_proba = models["model"].predict_proba(input_scaled)[0]

        logger.info(f"Prediction: {prediction_label}")
        logger.info(f"Prediction probabilities: {prediction_proba}")

        return jsonify(
            {
                "success": True,
                "level": prediction_label,
                "probabilities": prediction_proba.tolist(),
            }
        )
    except Exception as e:
        logger.error(f"Error in calculate-level: {str(e)}")
        logger.error(f"Error details: {type(e).__name__}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return (
            jsonify(
                {"success": False, "error": str(e), "error_type": type(e).__name__}
            ),
            400,
        )


@app.route("/api/predict-category", methods=["POST"])
def predict_category():
    try:
        data = request.get_json()
        course_data = data.get("course_data", {})
        logger.info(f"Received course data: {course_data}")

        # Extract text from course data
        title = course_data.get("title", "")
        description = course_data.get("description", "")
        content = course_data.get("content", "")

        # Combine text for classification
        full_text = f"{title} {description} {content}"
        logger.info(f"Combined text for classification: {full_text}")

        # Use the course classifier
        category, score = models["course_classifier"].classify_text(full_text)
        logger.info(f"Category prediction: {category}, score: {score}")

        return jsonify(
            {"success": True, "category": category, "confidence_score": float(score)}
        )
    except Exception as e:
        logger.error(f"Error in predict-category: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/predict-level", methods=["POST"])
def predict_level():
    try:
        data = request.get_json()
        course_data = data.get("course_data", {})
        logger.info(f"Received course data: {course_data}")

        # Extract text from course data
        title = course_data.get("title", "")
        description = course_data.get("description", "")
        content = course_data.get("content", "")

        # Combine text for classification
        full_text = f"{title} {description} {content}"
        logger.info(f"Combined text for classification: {full_text}")

        # Transform the text using the vectorizer
        text_vector = models["vectorizer"].transform([full_text])
        logger.info(f"Text vector shape: {text_vector.shape}")

        # Predict the level
        level = models["course_level_model"].predict(text_vector)
        logger.info(f"Level prediction: {level}")

        return jsonify({"success": True, "level": int(level[0])})
    except Exception as e:
        logger.error(f"Error in predict-level: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/generate-learning-path", methods=["POST"])
def generate_learning_path():
    try:
        data = request.get_json()
        user_data = data.get("user_data", {})
        logger.info(f"Received user data for learning path generation: {user_data}")

        # Extraire les données de l'utilisateur
        programming_language = user_data.get("subject", "")
        interests = user_data.get("interests", [])
        user_level = user_data.get("level", "beginner")

        # Vérifier les données requises
        if not programming_language:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Le langage de programmation est requis",
                    }
                ),
                400,
            )

        if not interests:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Au moins un centre d'intérêt est requis",
                    }
                ),
                400,
            )

        # Charger les cours depuis le fichier JSON
        courses_path = (
            Path(__file__).parent.parent / "data" / "course_pipeline" / "courses.json"
        )
        with open(courses_path, "r", encoding="utf-8") as f:
            all_courses = json.load(f)

        # Créer le profil utilisateur pour la recommandation
        user_profile = {
            "preferences": {"interests": [programming_language] + interests},
            "academic_background": {"highest_academic_level": int(user_level)},
        }

        # Prétraiter les cours
        processed_courses = preprocess_courses(all_courses)

        # Filtrer les cours selon le profil
        filtered_courses = filter_courses(user_profile, processed_courses)

        if not filtered_courses:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Aucun cours trouvé correspondant à vos critères",
                    }
                ),
                404,
            )

        # Recommander les cours
        recommended_courses = recommend_courses(
            user_profile, filtered_courses, top_k=15
        )

        # Préparer le prompt pour Claude
        prompt = f"""En tant qu'expert en enseignement de la programmation, analyse et organise les cours suivants pour créer un parcours d'apprentissage progressif en {programming_language}.
        
Cours disponibles:
{json.dumps(recommended_courses, indent=2, ensure_ascii=False)}

IMPORTANT: Ta réponse DOIT être UNIQUEMENT au format JSON valide, sans aucun texte supplémentaire avant ou après.

Pour chaque cours, tu dois:
1. Vérifier et améliorer la description si elle est trop courte ou manquante
2. S'assurer que chaque cours a une URL valide
3. Organiser les cours dans un ordre logique de progression
4. Créer des modules thématiques cohérents
5. Ajouter des prérequis pour chaque module
6. Suggérer des ressources complémentaires si nécessaire

Format JSON strict attendu (réponds UNIQUEMENT avec ce format, sans commentaires ni texte supplémentaire):
{{
    "modules": [
        {{
            "title": "Titre du module",
            "description": "Description détaillée du module",
            "prerequisites": ["prérequis 1", "prérequis 2"],
            "level": "niveau",
            "duration": "durée estimée",
            "courses": [
                {{
                    "title": "Titre du cours",
                    "description": "Description améliorée",
                    "url": "lien vers la ressource",
                    "category": "catégorie",
                    "level": "niveau",
                    "additional_resources": ["ressource 1", "ressource 2"]
                }}
            ]
        }}
    ]
}}

Rappel: Ta réponse doit être UNIQUEMENT le JSON ci-dessus, sans aucun texte supplémentaire."""

        # Appeler Claude pour analyser et organiser les cours
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4000,
            temperature=0.7,
            system="Tu es un expert en pédagogie et en programmation. Ta tâche est d'organiser des cours dans un ordre logique et progressif, en enrichissant les descriptions et en ajoutant des ressources complémentaires pertinentes. IMPORTANT: Tu dois TOUJOURS répondre en JSON valide, sans aucun texte supplémentaire.",
            messages=[{"role": "user", "content": prompt}],
        )

        # Parser la réponse de Claude
        try:
            claude_text = response.content[0].text
            logger.info(f"Claude response (first 500 chars): {claude_text[:500]}")
            
            # Nettoyer la réponse si nécessaire
            claude_text = claude_text.strip()
            if claude_text.startswith('```json'):
                # Retirer les marqueurs de code markdown
                claude_text = claude_text.replace('```json', '').replace('```', '').strip()
            
            claude_response = json.loads(claude_text)
            modules = claude_response.get("modules", [])
        except json.JSONDecodeError as e:
            logger.error(f"Erreur lors du parsing de la réponse de Claude: {e}")
            logger.error(f"Raw Claude response: {response.content[0].text}")
            return (
                jsonify(
                    {"success": False, "error": "Erreur lors de l'analyse des cours"}
                ),
                500,
            )

        # Générer le parcours d'apprentissage
        learning_path = {
            "language": programming_language,
            "level": user_level,
            "interests": interests,
            "modules": modules,
        }

        logger.info(f"Generated learning path: {learning_path}")

        return jsonify({"success": True, "learning_path": learning_path})

    except Exception as e:
        logger.error(f"Error in generate-learning-path: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/improve-learning-path", methods=["POST"])
def improve_learning_path():
    try:
        data = request.get_json()
        learning_path = data.get("learning_path")
        if not learning_path:
            return (
                jsonify(
                    {"success": False, "error": "Parcours d'apprentissage manquant"}
                ),
                400,
            )

        # Préparer le prompt pour Claude
        prompt = f"""En tant que conseiller pédagogique, analyse ce parcours d'apprentissage et propose des améliorations :

Parcours actuel :
- Langage : {learning_path.get('language')}
- Niveau : {learning_path.get('level')}
- Centres d'intérêt : {', '.join(learning_path.get('interests', []))}

Modules :
{json.dumps(learning_path.get('modules', []), indent=2, ensure_ascii=False)}

Je souhaite que tu analyses l'ensemble du parcours et que tu :
1. Évalues la progression logique globale des cours
4. Identifies les prérequis manquants dans l'ensemble

Format de réponse souhaité :
- Évaluation globale : [analyse de la progression d'ensemble]
- Ajustements suggérés : [liste des changements recommandés dans l'organisation]
- Cours complémentaires : [liste de suggestions pour enrichir le parcours]
- Prérequis à ajouter : [liste des prérequis manquants]

Merci de garder les suggestions concises et pratiques."""

        # Appel à l'API Claude
        improvements = call_claude_api(prompt)

        return jsonify(
            {
                "success": True,
                "improvements": improvements,
                "original_path": learning_path,
            }
        )
    except Exception as e:
        logger.error(f"Error in improve-learning-path: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/claude-advice", methods=["POST"])
def claude_advice_api():
    try:
        data = request.get_json()
        modules = data.get("modules")
        if not modules:
            return jsonify({"success": False, "error": "Modules manquants"}), 400

        # Préparer le prompt pour Claude
        prompt = f"""En tant que conseiller pédagogique, analyse ces modules et propose des conseils pour enrichir le parcours d'apprentissage :

Modules actuels :
{json.dumps(modules, indent=2, ensure_ascii=False)}

IMPORTANT: Ta réponse DOIT être UNIQUEMENT au format JSON valide, sans aucun texte supplémentaire avant ou après.

Pour chaque suggestion, tu dois :
1. Expliquer la pertinence du sujet en lien avec le parcours
2. Préciser le niveau de difficulté
3. Fournir des ressources gratuites en ligne
4. Limiter les suggestions à 3-4 sujets maximum

Format JSON strict attendu (réponds UNIQUEMENT avec ce format, sans commentaires ni texte supplémentaire) :
{{
    "suggestions": [
        {{
            "title": "Titre du sujet suggéré",
            "relevance": "Explication de la pertinence",
            "level": "débutant/intermédiaire/avancé",
            "resources": [
                {{
                    "name": "Nom de la ressource",
                    "url": "Lien vers la ressource",
                    "type": "Type de ressource (site web, vidéo, documentation, etc.)"
                }}
            ]
        }}
    ]
}}

Rappel: Ta réponse doit être UNIQUEMENT le JSON ci-dessus, sans aucun texte supplémentaire."""

        # Appeler Claude pour analyser et organiser les cours
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=4000,
            temperature=0.7,
            system="Tu es un expert en pédagogie et en programmation. Ta tâche est de suggérer des sujets complémentaires pertinents pour enrichir un parcours d'apprentissage. IMPORTANT: Tu dois TOUJOURS répondre en JSON valide, sans aucun texte supplémentaire.",
            messages=[{"role": "user", "content": prompt}],
        )

        # Parser la réponse de Claude
        try:
            claude_response = json.loads(response.content[0].text)
            suggestions = claude_response.get("suggestions", [])
        except json.JSONDecodeError:
            logger.error("Erreur lors du parsing de la réponse de Claude")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Erreur lors de l'analyse des suggestions",
                    }
                ),
                500,
            )

        return jsonify({"success": True, "suggestions": suggestions})

    except Exception as e:
        logger.error(f"Error in claude-advice: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate-quiz", methods=["POST"])
def generate_quiz():
    try:
        data = request.json
        learning_path = data.get("learning_path")

        if not learning_path:
            return (
                jsonify(
                    {"success": False, "error": "Parcours d'apprentissage manquant"}
                ),
                400,
            )

        # Initialiser le client Anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

        # Préparer le prompt pour Claude
        prompt = f"""En tant qu'expert en pédagogie, génère un quiz d'évaluation pour le parcours d'apprentissage suivant.
        IMPORTANT: Réponds UNIQUEMENT en format JSON valide, sans aucun autre texte.

        Parcours d'apprentissage:
        Langage: {learning_path['language']}
        Niveau: {learning_path['level']}
        Modules: {json.dumps(learning_path['modules'], ensure_ascii=False)}

        Format JSON strict attendu:
        {{
            "title": "Titre du quiz",
            "description": "Description du quiz",
            "passing_score": 70,
            "questions": [
                {{
                    "text": "Question",
                    "points": 1,
                    "answers": [
                        {{
                            "text": "Réponse",
                            "is_correct": true/false
                        }}
                    ]
                }}
            ]
        }}

        Règles pour le quiz:
        1. Crée 5-7 questions pertinentes couvrant les concepts clés du parcours
        2. Chaque question doit avoir 4 réponses possibles
        3. Une seule réponse correcte par question
        4. Les questions doivent être progressives en difficulté
        5. Inclus des questions sur la théorie et la pratique
        6. Assure-toi que les réponses sont claires et sans ambiguïté
        7. Le score de passage est de 70%

        IMPORTANT: Réponds UNIQUEMENT en format JSON valide."""

        # Appeler Claude
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4000,
            temperature=0.7,
            system="Tu es un expert en pédagogie qui crée des quiz d'évaluation. Réponds UNIQUEMENT en format JSON valide.",
            messages=[{"role": "user", "content": prompt}],
        )

        # Extraire et parser la réponse JSON
        quiz_data = json.loads(response.content[0].text)

        return jsonify({"success": True, "quiz": quiz_data})

    except Exception as e:
        logger.error(f"Erreur lors de la génération du quiz: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# ===============================================
# NOUVELLES ROUTES COMPATIBLES DJANGO
# ===============================================


@app.route("/health", methods=["GET"])
def health_check_django():
    """Endpoint de santé compatible Django"""
    return jsonify(
        {
            "status": "healthy",
            "service": "learning_platform_pipeline",
            "pipeline_ready": True,
            "elasticsearch_configured": bool(ELASTICSEARCH_HOST),
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.route("/status", methods=["GET"])
def get_status_django():
    """Statut détaillé du pipeline compatible Django"""
    # Ajouter le statut Spark
    spark_status = spark_service.get_cluster_status()

    return jsonify(
        {
            "status": "running",
            "processed_courses": processed_courses_count,
            "last_processed": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "spark_cluster": spark_status,
            "processing_modes": {
                "local": True,
                "distributed": spark_status.get("enabled", False),
                "active_workers": spark_status.get("active_workers", 0),
            },
        }
    )


@app.route("/process-single-course", methods=["POST"])
def process_single_course_django():
    """
    Traite un cours unique avec le pipeline et l'envoie à Elasticsearch
    Compatible avec l'intégration Django
    """
    global processed_courses_count

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Aucune donnée reçue"}), 400

        # Validation des champs requis (titre et id seulement, description optionnelle)
        if not data.get("id"):
            return jsonify({"error": "Champ requis manquant: id"}), 400

        if not data.get("titre"):
            return jsonify({"error": "Champ requis manquant: titre"}), 400

        # La description est optionnelle, on met une valeur par défaut
        if not data.get("description"):
            data["description"] = (
                f"Cours sur {data.get('titre', 'un sujet informatique')}"
            )

        logger.info(f"🔄 Traitement du cours: {data.get('titre')}")

        # Traitement avec le pipeline
        pipeline_result = process_course_with_pipeline(data)

        # Enrichir les données du cours
        enriched_course = {
            "id": data["id"],
            "titre": data["titre"],
            "description": data["description"],
            "contenus": data.get("contenus", {}),
            "url": data.get("url", ""),
            "lien": data.get("lien", ""),
            "categories": (
                data.get("categories", [])
                if isinstance(data.get("categories"), list)
                else [data.get("categories")]
            )
            + [pipeline_result["predicted_category"]],
            "niveau": pipeline_result["predicted_level"],
            "duree": data.get("duree", ""),
            "predicted_category": pipeline_result["predicted_category"],
            "category_confidence": pipeline_result["category_confidence"],
            "predicted_level": pipeline_result["predicted_level"],
            "level_confidence": pipeline_result["level_confidence"],
            "vecteur_embedding": pipeline_result["vecteur_embedding"],
            "processed_at": datetime.utcnow().isoformat(),
        }

        # Envoyer directement à Elasticsearch
        elasticsearch_success = send_to_elasticsearch(enriched_course)

        if not elasticsearch_success:
            logger.warning(f"⚠️ Échec envoi Elasticsearch pour: {data.get('titre')}")

        processed_courses_count += 1
        logger.info(
            f"✅ Cours traité et {'indexé' if elasticsearch_success else 'traité'}: {data.get('titre')}"
        )

        return jsonify(enriched_course)

    except Exception as e:
        logger.error(f"❌ Erreur traitement cours: {str(e)}")
        return jsonify({"error": f"Erreur de traitement: {str(e)}"}), 500


@app.route("/process-courses-batch", methods=["POST"])
def process_courses_batch_django():
    """
    Traite un lot de cours avec le pipeline et les envoie à Elasticsearch
    Compatible avec l'intégration Django
    """
    global processed_courses_count

    try:
        courses_data = request.get_json()

        if not courses_data or not isinstance(courses_data, list):
            return jsonify({"error": "Données invalides: liste de cours attendue"}), 400

        logger.info(f"🔄 Traitement en lot de {len(courses_data)} cours")

        enriched_courses = []
        elasticsearch_successes = 0

        for course_data in courses_data:
            try:
                # Validation des champs requis (titre et id seulement, description optionnelle)
                if not course_data.get("id"):
                    logger.error(f"Champ manquant id pour cours {course_data}")
                    continue

                if not course_data.get("titre"):
                    logger.error(
                        f"Champ manquant titre pour cours {course_data.get('id', 'unknown')}"
                    )
                    continue

                # La description est optionnelle, on met une valeur par défaut
                if not course_data.get("description"):
                    course_data["description"] = (
                        f"Cours sur {course_data.get('titre', 'un sujet informatique')}"
                    )

                # Traitement avec le pipeline
                pipeline_result = process_course_with_pipeline(course_data)

                # Enrichir les données du cours
                enriched_course = {
                    "id": course_data["id"],
                    "titre": course_data["titre"],
                    "description": course_data["description"],
                    "contenus": course_data.get("contenus", {}),
                    "url": course_data.get("url", ""),
                    "lien": course_data.get("lien", ""),
                    "categories": (
                        course_data.get("categories", [])
                        if isinstance(course_data.get("categories"), list)
                        else [course_data.get("categories")]
                    )
                    + [pipeline_result["predicted_category"]],
                    "niveau": pipeline_result["predicted_level"],
                    "duree": course_data.get("duree", ""),
                    "predicted_category": pipeline_result["predicted_category"],
                    "category_confidence": pipeline_result["category_confidence"],
                    "predicted_level": pipeline_result["predicted_level"],
                    "level_confidence": pipeline_result["level_confidence"],
                    "vecteur_embedding": pipeline_result["vecteur_embedding"],
                    "processed_at": datetime.utcnow().isoformat(),
                }

                # Envoyer à Elasticsearch
                if send_to_elasticsearch(enriched_course):
                    elasticsearch_successes += 1

                enriched_courses.append(enriched_course)
                processed_courses_count += 1

            except Exception as e:
                logger.error(
                    f"Erreur traitement cours {course_data.get('id', 'unknown')}: {e}"
                )
                continue

        logger.info(
            f"✅ Lot terminé: {len(enriched_courses)} cours traités, {elasticsearch_successes} indexés"
        )

        return jsonify(enriched_courses)

    except Exception as e:
        logger.error(f"❌ Erreur traitement lot: {str(e)}")
        return jsonify({"error": f"Erreur de traitement en lot: {str(e)}"}), 500


@app.route("/stats/processed-courses", methods=["GET"])
def get_processed_courses_stats_django():
    """Statistiques des cours traités - Compatible Django"""
    spark_metrics = spark_service.get_performance_metrics()

    return jsonify(
        {
            "count": processed_courses_count,
            "timestamp": datetime.utcnow().isoformat(),
            "spark_metrics": spark_metrics,
        }
    )


@app.route("/process-courses-distributed", methods=["POST"])
def process_courses_distributed():
    """
    Traite les cours de manière distribuée avec Apache Spark
    Nouveau endpoint pour les calculs distribués
    """
    try:
        data = request.get_json()
        courses_data = data if isinstance(data, list) else data.get("courses", [])

        if not courses_data:
            return jsonify({"error": "Aucun cours fourni"}), 400

        logger.info(f"🚀 Traitement distribué demandé pour {len(courses_data)} cours")

        # Vérifier si Spark est disponible
        if not spark_service.is_cluster_available():
            logger.warning("Cluster Spark non disponible - fallback local")
            return process_courses_batch_django()

        # Soumettre le job au cluster Spark
        job_result = spark_service.submit_course_processing_job(courses_data)

        if "error" in job_result:
            # Fallback vers traitement local
            logger.warning("Erreur Spark - fallback local")
            return process_courses_batch_django()

        return jsonify(
            {
                "job_submitted": True,
                "job_id": job_result.get("job_id"),
                "course_count": len(courses_data),
                "estimated_duration": job_result.get("estimated_duration"),
                "status_url": f"/spark/job-status/{job_result.get('job_id')}",
                "processing_mode": "distributed",
            }
        )

    except Exception as e:
        logger.error(f"❌ Erreur traitement distribué: {str(e)}")
        return jsonify({"error": f"Erreur traitement distribué: {str(e)}"}), 500


@app.route("/spark/job-status/<job_id>", methods=["GET"])
def get_spark_job_status(job_id):
    """Récupère le statut d'un job Spark"""
    try:
        status = spark_service.get_job_status(job_id)
        return jsonify(status)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/spark/job-results/<job_id>", methods=["GET"])
def get_spark_job_results(job_id):
    """Récupère les résultats d'un job Spark"""
    try:
        results = spark_service.get_job_results(job_id)

        if results:
            return jsonify(results)
        else:
            return jsonify({"error": "Résultats non trouvés"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0", port=5000, debug=True
    )  # Port 5000 pour correspondre à la config Docker


@app.route("/api-docs", methods=["GET"])
def api_documentation_json():
    """
    Route alternative qui retourne la documentation en JSON
    """
    routes_info = {
        "api_name": "InLearning Platform API",
        "version": "1.0.0",
        "description": "API pour la plateforme d'apprentissage avec IA et Big Data",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "endpoints": {
            "/": {
                "methods": ["GET"],
                "description": "Documentation HTML de l'API",
                "parameters": "Aucun",
                "returns": "Page HTML avec documentation complète",
            },
            "/api-docs": {
                "methods": ["GET"],
                "description": "Documentation JSON de l'API",
                "parameters": "Aucun",
                "returns": "Documentation complète en format JSON",
            },
            "/health": {
                "methods": ["GET"],
                "description": "Vérification de l'état de santé de l'API",
                "parameters": "Aucun",
                "returns": "{'status': 'healthy', 'timestamp': '...'}",
            },
        },
    }

    return jsonify(routes_info)
