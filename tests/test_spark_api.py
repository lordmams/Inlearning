#!/usr/bin/env python3
"""
Script de test pour l'API Learning Platform (compatible Django)
"""

import requests
import json
import sys
from datetime import datetime

def test_api_health():
    """Teste l'endpoint /health"""
    print("🔍 Test de l'endpoint /health...")
    
    try:
        response = requests.get('http://localhost:8000/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check OK: {data}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur health check: {str(e)}")
        return False

def test_api_status():
    """Teste l'endpoint /status"""
    print("\n📊 Test de l'endpoint /status...")
    
    try:
        response = requests.get('http://localhost:8000/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status OK: {data}")
            return True
        else:
            print(f"❌ Status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur status: {str(e)}")
        return False

def test_single_course():
    """Teste l'endpoint /process-single-course"""
    print("\n🚀 Test de traitement d'un cours unique...")
    
    course_data = {
        "id": "test_course_001",
        "titre": "Python pour débutants",
        "description": "Apprenez les bases de Python avec ce cours complet",
        "contenus": {
            "paragraphs": [
                "Introduction à Python et son écosystème",
                "Variables, types de données et opérateurs",
                "Structures de contrôle: conditions et boucles"
            ],
            "lists": [
                ["Variables", "Functions", "Classes"],
                ["if", "while", "for"]
            ],
            "examples": [
                "print('Hello World')",
                "x = 5\nprint(x)",
                "def hello():\n    return 'Bonjour'"
            ],
            "texte": "Python est un langage de programmation puissant et facile à apprendre.",
            "lienVideo": "https://example.com/python-intro-video"
        },
        "url": "https://example.com/python-course",
        "lien": "https://example.com/python-course/details",
        "categories": ["Programmation", "Débutant"],
        "niveau": "Débutant",
        "duree": "4 semaines",
        "metadata": {
            "source": "test_script",
            "import_timestamp": datetime.utcnow().isoformat(),
            "original_format": "test_json"
        }
    }
    
    try:
        response = requests.post(
            'http://localhost:8000/process-single-course',
            json=course_data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Cours traité avec succès!")
            print(f"   Titre: {result.get('titre')}")
            print(f"   Catégorie prédite: {result.get('predicted_category')}")
            print(f"   Niveau prédit: {result.get('predicted_level')}")
            print(f"   Confiance catégorie: {result.get('category_confidence')}")
            print(f"   Embedding size: {len(result.get('vecteur_embedding', []))}")
            return True
        else:
            print(f"❌ Erreur traitement cours: {response.status_code}")
            print(f"   Détails: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        return False

def test_batch_courses():
    """Teste l'endpoint /process-courses-batch"""
    print("\n📦 Test de traitement en lot...")
    
    courses_data = [
        {
            "id": "batch_001",
            "titre": "JavaScript ES6+",
            "description": "Maîtrisez les nouvelles fonctionnalités de JavaScript",
            "contenus": {
                "paragraphs": ["Présentation d'ES6", "Arrow functions et classes"],
                "lists": [["const", "let", "arrow functions"]],
                "examples": ["const x = () => 'Hello'"],
                "texte": "JavaScript moderne pour le web",
                "lienVideo": ""
            },
            "categories": ["Web", "JavaScript"],
            "niveau": "Intermédiaire",
            "duree": "3 semaines"
        },
        {
            "id": "batch_002", 
            "titre": "Machine Learning avec Python",
            "description": "Introduction à l'apprentissage automatique",
            "contenus": {
                "paragraphs": ["Concepts de base du ML", "Algorithmes supervisés"],
                "lists": [["scikit-learn", "pandas", "numpy"]],
                "examples": ["from sklearn import datasets"],
                "texte": "Découvrez le machine learning",
                "lienVideo": ""
            },
            "categories": ["IA", "Python"],
            "niveau": "Avancé",
            "duree": "6 semaines"
        }
    ]
    
    try:
        response = requests.post(
            'http://localhost:8000/process-courses-batch',
            json=courses_data,
            headers={'Content-Type': 'application/json'},
            timeout=60
        )
        
        if response.status_code == 200:
            results = response.json()
            print(f"✅ Lot de {len(results)} cours traité avec succès!")
            for i, result in enumerate(results):
                print(f"   Cours {i+1}: {result.get('titre')} → {result.get('predicted_category')}")
            return True
        else:
            print(f"❌ Erreur traitement lot: {response.status_code}")
            print(f"   Détails: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test batch: {str(e)}")
        return False

def test_stats():
    """Teste l'endpoint /stats/processed-courses"""
    print("\n📈 Test de l'endpoint /stats...")
    
    try:
        response = requests.get('http://localhost:8000/stats/processed-courses', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Stats OK: {data}")
            return True
        else:
            print(f"❌ Stats failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur stats: {str(e)}")
        return False

def test_root():
    """Teste l'endpoint racine /"""
    print("\n🏠 Test de l'endpoint racine...")
    
    try:
        response = requests.get('http://localhost:8000/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Root endpoint OK:")
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Ready: {data.get('ready')}")
            return True
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur root endpoint: {str(e)}")
        return False

def main():
    """Fonction principale de test"""
    print("🧪 Test de l'API Spark Pipeline")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_api_health),
        ("Status", test_api_status), 
        ("Root Endpoint", test_root),
        ("Single Course", test_single_course),
        ("Batch Courses", test_batch_courses),
        ("Stats", test_stats)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- Test: {test_name} ---")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSÉ")
            else:
                print(f"❌ {test_name} ÉCHOUÉ")
        except Exception as e:
            print(f"❌ {test_name} ERREUR: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"📊 Résultats: {passed}/{total} tests réussis")
    
    if passed == total:
        print("🎉 Tous les tests sont passés! L'API Learning Platform fonctionne correctement.")
        print("\n📋 L'API traite ET envoie directement à Elasticsearch:")
        print("- Health: http://localhost:8000/health")
        print("- Status: http://localhost:8000/status")
        print("- Process: http://localhost:8000/process-single-course")
        print("- Batch: http://localhost:8000/process-courses-batch")
        print("\n🔥 AVANTAGES:")
        print("  ✅ Classification automatique des catégories")
        print("  ✅ Prédiction intelligente des niveaux")
        print("  ✅ Génération d'embeddings") 
        print("  ✅ Indexation directe dans Elasticsearch")
    else:
        print("⚠️ Certains tests ont échoué.")
        print("Vérifiez que l'API est démarrée avec: cd learning_platform/api && python app.py")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 