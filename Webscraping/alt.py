import requests
import json

def recuperer_cours_programmation():
    """
    Récupère des cours de programmation via des APIs publiques
    """
    apis = [
        {
            'nom': 'Coursera',
            'url': 'https://www.coursera.org/api/courses.v1',
            'params': {
                'q': 'search',
                'query': 'programming',
                'includes': 'v1specialization'
            }
        },
        {
            'nom': 'edX',
            'url': 'https://edge.edx.org/api/courses/v1/courses/',
            'params': {
                'search_term': 'programming',
                'page_size': 50
            }
        }
    ]
    
    cours_complets = []
    
    for api in apis:
        try:
            response = requests.get(api['url'], params=api['params'])
            
            if response.status_code == 200:
                data = response.json()
                
                # Extraction adaptée selon la structure de chaque API
                if api['nom'] == 'Coursera':
                    cours = [{
                        'plateforme': 'Coursera',
                        'titre': cours.get('name', 'Titre non disponible'),
                        'description': cours.get('description', ''),
                        'niveau': 'Débutant'
                    } for cours in data.get('elements', [])]
                
                elif api['nom'] == 'edX':
                    cours = [{
                        'plateforme': 'edX',
                        'titre': cours.get('name', 'Titre non disponible'),
                        'url': cours.get('course_image_url', ''),
                        'niveau': 'Intermédiaire'
                    } for cours in data.get('results', [])]
                
                cours_complets.extend(cours)
            
        except Exception as e:
            print(f"Erreur avec {api['nom']}: {e}")
    
    return cours_complets

# Récupération et affichage des cours
cours_programmation = recuperer_cours_programmation()
print(json.dumps(cours_programmation, indent=2, ensure_ascii=False))