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
from models.search_engine.app import recherche_semantique

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the course classifier and parcours generation modules
from models.course_pipeline.course_classifier import CourseClassifier, CATEGORIES

app = Flask(__name__)
CORS(app)

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
        recommended_courses = recommend_courses(user_profile, filtered_courses, top_k=10)

        # Organiser les cours en modules
        modules = []
        current_level = 1
        current_module = {
            'title': f'Module {current_level}: Introduction à {programming_language}',
            'level': user_level,
            'courses': []
        }

        for course in recommended_courses:
            course_level = course.get('niveau', 1)
            
            # Si le niveau change significativement, créer un nouveau module
            if course_level > current_level + 1:
                if current_module['courses']:
                    modules.append(current_module)
                current_level = course_level
                current_module = {
                    'title': f'Module {current_level}: {programming_language} Avancé',
                    'level': 'advanced' if current_level > 2 else 'intermediate',
                    'duration': '3 semaines',
                    'courses': []
                }
            
          
            # Ajouter le cours au module actuel
            current_module['courses'].append({
                'title': course.get('titre', ''),
                'description': course.get('description', ''),
                'category': course.get('categories', ''),
                'level': course.get('niveau', 1),
                'url': course.get('lien', ''),
                
            })

        # Ajouter le dernier module s'il contient des cours
        if current_module['courses']:
            modules.append(current_module)

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

@app.route('/api/semantic-search', methods=['POST'])
def semantic_search():
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'La requête de recherche est requise'
            }), 400

        # Charger les cours depuis le fichier JSON
        courses_file =  Path(__file__).parent.parent / 'data' / 'course_pipeline' / 'courses.json'
        with open(courses_file, 'r', encoding='utf-8') as f:
            courses = json.load(f)

        # Convertir les cours en DataFrame pour la recherche sémantique
        df = pd.DataFrame(courses)
        
        # Adapter les noms de colonnes pour compatibilité avec le script de recherche
        df = df.rename(columns={
            'title': 'titre',
            'content': 'contenus',
            'category': 'categorie',
            'level': 'niveau',
            'duration': 'duree',
            'url': 'lien'
        })

        # S'assurer que 'contenus' est bien un dict avec 'paragraphs'
        if 'contenus' in df.columns:
            df['contenus'] = df['contenus'].apply(lambda c: c if isinstance(c, dict) else {'paragraphs': []})
        else:
            df['contenus'] = [{} for _ in range(len(df))]

        # Construction du texte complet
        df["texte_complet"] = df.apply(
            lambda row: f"{row.get('titre', '')} {row.get('description', '')} {' '.join(row.get('contenus', {}).get('paragraphs', []))}",
            axis=1
        )

        # Initialiser le modèle de transformation de phrases
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Encoder les textes des cours
        embeddings = model.encode(df["texte_complet"].tolist(), show_progress_bar=True)

        # Effectuer la recherche sémantique
        results = recherche_semantique(
            df=df,
            embeddings=embeddings,
            model=model,
            requete=data['query'],
            n_results=data.get('n_results', 10),
            min_score=data.get('min_score', 0.3)
        )

        # Formater les résultats
        formatted_results = []
        for _, row in results.iterrows():
            formatted_results.append({
                'title': row.get('titre', ''),
                'description': row.get('description', ''),
                'category': row.get('categorie', ''),
                'level': row.get('niveau', ''),
                'duration': row.get('duree', ''),
                'url': row.get('lien', ''),
                'score': float(row['similarite'])
            })

        return jsonify({
            'success': True,
            'results': formatted_results
        })

    except Exception as e:
        logger.error(f"Erreur lors de la recherche sémantique: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Une erreur est survenue lors de la recherche'
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)