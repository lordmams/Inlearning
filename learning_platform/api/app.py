from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import joblib
import pickle
from pathlib import Path
import numpy as np
import pandas as pd
import logging
import json
from models.parcours_generation.recommender import recommend_courses
from models.parcours_generation.preprocessing import preprocess_courses
from models.parcours_generation.filtering import filter_courses
from models.parcours_generation.sequencing import order_courses
import anthropic
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the course classifier and parcours generation modules
from models.course_pipeline.course_classifier import CourseClassifier, CATEGORIES

app = Flask(__name__)
CORS(app)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
logger.info(f"ANTHROPIC_API_KEY loaded: {'Yes' if ANTHROPIC_API_KEY else 'No'}")
logger.info(f"ANTHROPIC_API_KEY length: {len(ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else 0}")

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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        logger.info("Received response from Claude API")
        # Pour la version anthropic>=0.7.7
        return response.content[0].text if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        return f"Erreur lors de l'appel à Claude : {e}"

def load_models():
    models_dir = Path(__file__).parent.parent / 'models'
    logger.info(f"Loading models from: {models_dir}")
    
    try:
        # Load the student level model and its components
        student_level_model_path = models_dir / 'student_level' / 'best_model_rff.pkl'
        logger.info(f"Loading student level model from: {student_level_model_path}")
        model_details = joblib.load(student_level_model_path)
        
        # Extract components
        model = model_details['model']
        scaler = model_details['scaler']
        label_encoder = model_details['label_encoder']
        feature_mappings = model_details['feature_mappings']
        features = model_details['features']
        
        logger.info("Student level model components loaded successfully")
        logger.info(f"Available features: {features}")
        logger.info(f"Feature mappings: {feature_mappings}")
        
    except Exception as e:
        logger.error(f"Error loading student level model: {str(e)}")
        raise
    
    try:
        # Load the course level model and vectorizer
        course_level_model_path = models_dir / 'course_pipeline' / 'level_model.joblib'
        vectorizer_path = models_dir / 'course_pipeline' / 'vectorizer.joblib'
        
        logger.info(f"Loading course level model from: {course_level_model_path}")
        course_level_model = joblib.load(course_level_model_path)
        logger.info(f"Course level model loaded successfully: {type(course_level_model)}")
        
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
        'model': model,
        'scaler': scaler,
        'label_encoder': label_encoder,
        'feature_mappings': feature_mappings,
        'features': features,
        'course_level_model': course_level_model,
        'vectorizer': vectorizer,
        'course_classifier': course_classifier
    }

# Load models at startup
logger.info("Starting to load models...")
models = load_models()
logger.info("All models loaded successfully")

@app.route('/api/calculate-level', methods=['POST'])
def calculate_user_level():
    try:
        data = request.get_json()
        user_data = data.get('user_data', {})
        logger.info(f"Received user data: {user_data}")
        
        # Log the available feature mappings
        logger.info(f"Available gender mappings: {models['feature_mappings']['gender']}")
        logger.info(f"Available language mappings: {models['feature_mappings']['preferred_language']}")
        logger.info(f"Available learning mode mappings: {models['feature_mappings']['learning_mode']}")
        logger.info(f"Available academic level mappings: {models['feature_mappings']['highest_academic_level']}")
        logger.info(f"Available field of study mappings: {models['feature_mappings']['fields_of_study']}")
        
        # Safely get mapped values with defaults
        def get_mapped_value(mapping_dict, key, default_key):
            try:
                # First try to get the provided key
                if key in mapping_dict:
                    return mapping_dict[key]
                # If not found, use the first available key as default
                default_value = next(iter(mapping_dict.values()))
                logger.warning(f"Key '{key}' not found in mappings. Using default value: {default_value}")
                return default_value
            except Exception as e:
                logger.error(f"Error in get_mapped_value: {str(e)}")
                # Return the first available value as a last resort
                return next(iter(mapping_dict.values()))
        
        # Create input DataFrame with the correct features
        input_data = pd.DataFrame({
            "age": [user_data.get('age', 0)],
            "gender": [get_mapped_value(models['feature_mappings']['gender'], 
                                     user_data.get('gender', ''), '')],
            "preferred_language": [get_mapped_value(models['feature_mappings']['preferred_language'],
                                                 user_data.get('preferred_language', ''), '')],
            "learning_mode": [get_mapped_value(models['feature_mappings']['learning_mode'],
                                            user_data.get('learning_mode', ''), '')],
            "highest_academic_level": [get_mapped_value(models['feature_mappings']['highest_academic_level'],
                                                     user_data.get('highest_academic_level', ''), '')],
            "total_experience_years": [user_data.get('total_experience_years', 0)],
            "fields_of_study": [get_mapped_value(models['feature_mappings']['fields_of_study'],
                                              user_data.get('fields_of_study', ''), '')]
        })
        
        logger.info(f"Input data: {input_data}")
        
        # Scale the features
        input_scaled = models['scaler'].transform(input_data[models['features']])
        logger.info(f"Scaled input: {input_scaled}")
        
        # Make prediction
        prediction = models['model'].predict(input_scaled)
        prediction_label = models['label_encoder'].inverse_transform(prediction)[0]
        prediction_proba = models['model'].predict_proba(input_scaled)[0]
        
        logger.info(f"Prediction: {prediction_label}")
        logger.info(f"Prediction probabilities: {prediction_proba}")
        
        return jsonify({
            'success': True,
            'level': prediction_label,
            'probabilities': prediction_proba.tolist()
        })
    except Exception as e:
        logger.error(f"Error in calculate-level: {str(e)}")
        logger.error(f"Error details: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 400

@app.route('/api/predict-category', methods=['POST'])
def predict_category():
    try:
        data = request.get_json()
        course_data = data.get('course_data', {})
        logger.info(f"Received course data: {course_data}")
        
        # Extract text from course data
        title = course_data.get('title', '')
        description = course_data.get('description', '')
        content = course_data.get('content', '')
        
        # Combine text for classification
        full_text = f"{title} {description} {content}"
        logger.info(f"Combined text for classification: {full_text}")
        
        # Use the course classifier
        category, score = models['course_classifier'].classify_text(full_text)
        logger.info(f"Category prediction: {category}, score: {score}")
        
        return jsonify({
            'success': True,
            'category': category,
            'confidence_score': float(score)
        })
    except Exception as e:
        logger.error(f"Error in predict-category: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/predict-level', methods=['POST'])
def predict_level():
    try:
        data = request.get_json()
        course_data = data.get('course_data', {})
        logger.info(f"Received course data: {course_data}")
        
        # Extract text from course data
        title = course_data.get('title', '')
        description = course_data.get('description', '')
        content = course_data.get('content', '')
        
        # Combine text for classification
        full_text = f"{title} {description} {content}"
        logger.info(f"Combined text for classification: {full_text}")
        
        # Transform the text using the vectorizer
        text_vector = models['vectorizer'].transform([full_text])
        logger.info(f"Text vector shape: {text_vector.shape}")
        
        # Predict the level
        level = models['course_level_model'].predict(text_vector)
        logger.info(f"Level prediction: {level}")
        
        return jsonify({
            'success': True,
            'level': int(level[0])
        })
    except Exception as e:
        logger.error(f"Error in predict-level: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/generate-learning-path', methods=['POST'])
def generate_learning_path():
    try:
        data = request.get_json()
        user_data = data.get('user_data', {})
        logger.info(f"Received user data for learning path generation: {user_data}")

        # Extraire les données de l'utilisateur
        programming_language = user_data.get('subject', '')
        interests = user_data.get('interests', [])
        user_level = user_data.get('level', 'beginner')

        # Vérifier les données requises
        if not programming_language:
            return jsonify({
                'success': False,
                'error': 'Le langage de programmation est requis'
            }), 400

        if not interests:
            return jsonify({
                'success': False,
                'error': 'Au moins un centre d\'intérêt est requis'
            }), 400

        # Charger les cours depuis le fichier JSON
        courses_path = Path(__file__).parent.parent / 'data' / 'course_pipeline' / 'courses.json'
        with open(courses_path, 'r', encoding='utf-8') as f:
            all_courses = json.load(f)

        # Créer le profil utilisateur pour la recommandation
        user_profile = {
            "preferences": {
                "interests": [programming_language] + interests
            },
            "academic_background": {
                "highest_academic_level": int(user_level)
            }
        }

        # Prétraiter les cours
        processed_courses = preprocess_courses(all_courses)
        
        # Filtrer les cours selon le profil
        filtered_courses = filter_courses(user_profile, processed_courses)
        
        if not filtered_courses:
            return jsonify({
                'success': False,
                'error': 'Aucun cours trouvé correspondant à vos critères'
            }), 404

        # Recommander les cours
        recommended_courses = recommend_courses(user_profile, filtered_courses, top_k=15)

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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parser la réponse de Claude
        try:
            claude_response = json.loads(response.content[0].text)
            modules = claude_response.get('modules', [])
        except json.JSONDecodeError:
            logger.error("Erreur lors du parsing de la réponse de Claude")
            return jsonify({
                'success': False,
                'error': 'Erreur lors de l\'analyse des cours'
            }), 500

        # Générer le parcours d'apprentissage
        learning_path = {
            'language': programming_language,
            'level': user_level,
            'interests': interests,
            'modules': modules
        }

        logger.info(f"Generated learning path: {learning_path}")

        return jsonify({
            'success': True,
            'learning_path': learning_path
        })

    except Exception as e:
        logger.error(f"Error in generate-learning-path: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/improve-learning-path', methods=['POST'])
def improve_learning_path():
    try:
        data = request.get_json()
        learning_path = data.get('learning_path')
        if not learning_path:
            return jsonify({'success': False, 'error': 'Parcours d\'apprentissage manquant'}), 400

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

        return jsonify({
            'success': True,
            'improvements': improvements,
            'original_path': learning_path
        })
    except Exception as e:
        logger.error(f"Error in improve-learning-path: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/claude-advice', methods=['POST'])
def claude_advice_api():
    try:
        data = request.get_json()
        modules = data.get('modules')
        if not modules:
            return jsonify({'success': False, 'error': 'Modules manquants'}), 400

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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parser la réponse de Claude
        try:
            claude_response = json.loads(response.content[0].text)
            suggestions = claude_response.get('suggestions', [])
        except json.JSONDecodeError:
            logger.error("Erreur lors du parsing de la réponse de Claude")
            return jsonify({
                'success': False,
                'error': 'Erreur lors de l\'analyse des suggestions'
            }), 500

        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        logger.error(f"Error in claude-advice: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/generate-quiz', methods=['POST'])
def generate_quiz():
    try:
        data = request.json
        learning_path = data.get('learning_path')
        
        if not learning_path:
            return jsonify({
                'success': False,
                'error': 'Parcours d\'apprentissage manquant'
            }), 400

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
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extraire et parser la réponse JSON
        quiz_data = json.loads(response.content[0].text)
        
        return jsonify({
            'success': True,
            'quiz': quiz_data
        })

    except Exception as e:
        logger.error(f"Erreur lors de la génération du quiz: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)