import anthropic
import json
import random
import os
import time

# Configuration de l'API pour Claude
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
# Fonction pour appeler l'API Claude
def call_claude(prompt, max_tokens=8192):
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=max_tokens,
        temperature=0.7,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    return message.content[0].text

# Fonction pour générer des données avec Claude
def generate_student_data(prompt_template, n_samples=1000, profiles=None, batch_size=10):
    if profiles is None:
        profiles = ["étudiant", "reconversion", "professionnel en poste"]

    all_data = []
    num_batches = (n_samples + batch_size - 1) // batch_size  # Arrondi supérieur

    for batch_num in range(num_batches):
        current_batch_size = min(batch_size, n_samples - len(all_data))
        
        # Construire le prompt pour le batch actuel
        prompt = f"Générez exactement {current_batch_size} exemples de personnes selon le format suivant. "
        prompt += f"Assurez-vous d'avoir de la variété dans les profils ({', '.join(profiles)}) "
        prompt += "et les âges (18-50 ans). Retournez uniquement un tableau JSON valide contenant "
        prompt += f"les {current_batch_size} exemples, sans texte additionnel.\n\n"
        prompt += prompt_template

        try:
            print(f"\nGénération du batch {batch_num + 1}/{num_batches} "
                  f"({current_batch_size} exemples)...")
            
            response_text = call_claude(prompt)
            batch_data = json.loads(response_text)
            
            if isinstance(batch_data, list):
                all_data.extend(batch_data)
                print(f"Batch {batch_num + 1} complété : "
                      f"{len(batch_data)} exemples générés. "
                      f"Total : {len(all_data)}/{n_samples}")
            else:
                print(f"Erreur : La réponse n'est pas un tableau JSON valide")
            
            # Petite pause entre les batchs pour éviter les limitations d'API
            if batch_num < num_batches - 1:
                time.sleep(2)

        except Exception as e:
            print(f"Erreur lors de la génération du batch {batch_num + 1} : {e}")
            continue

    return all_data

# Exemple de prompt template (reste inchangé)
prompt_template = """
[
  {
    "person": {
      "id": "ID_UNIQUE",
      "name": "NOM_PRENOM",
      "age": "AGE_18_50",
      "gender": "GENRE"
    },
    "preferences": {
      "preferred_language": "LANGUE",
      "learning_mode": "MODE_APPRENTISSAGE",
      "interests": ["INTERET1", "INTERET2"]
    },
    "academic_background": {
      "highest_academic_level": "NIVEAU",
      "fields_of_study": [
        {
          "field_name": "DOMAINE",
          "institution": "INSTITUTION",
          "year_of_completion": "ANNEE"
        }
      ]
    },
    "professional_background": {
      "total_experience_years": "EXPERIENCE",
      "jobs": [
        {
          "title": "TITRE",
          "company": "ENTREPRISE",
          "duration_years": "DUREE"
        }
      ]
    },
    "goals": {
      "short_term_goals": ["OBJECTIF_CT1", "OBJECTIF_CT2"],
      "long_term_goals": ["OBJECTIF_LT1", "OBJECTIF_LT2"]
    }
  }
]

Instructions supplémentaires:
- Variez les profils entre étudiants, personnes en reconversion, et professionnels en poste
- Les âges doivent être réalistes et cohérents avec le profil
- L'expérience professionnelle doit être cohérente avec l'âge
- Incluez des parcours académiques variés et réalistes
- Les objectifs doivent être cohérents avec le profil
- Utilisez des noms et prénoms français réalistes
- Assurez-vous que chaque exemple est unique
"""

# Générer les données
data = generate_student_data(prompt_template, n_samples=100, batch_size=20)

# Sauvegarder les données générées dans un fichier JSON
with open("generated_student_data.json", "w", encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("\nDonnées générées et sauvegardées dans 'generated_student_data.json'")