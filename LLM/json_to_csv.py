import pandas as pd
import json


# Fonction pour convertir un fichier JSON en CSV
def convert_json_to_csv(json_file_path, csv_file_path):
    # Charger les données JSON
    with open(json_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    # Préparer les données pour un format tabulaire
    processed_data = []

    for entry in data:
        # Extraire les sections principales
        person = entry.get("person", {})
        preferences = entry.get("preferences", {})
        academic_background = entry.get("academic_background", {})
        professional_background = entry.get("professional_background", {})
        goals = entry.get("goals", {})

        # Transformer les champs imbriqués en colonnes
        processed_data.append(
            {
                "id": person.get("id", ""),
                "name": person.get("name", ""),
                "age": person.get("age", ""),
                "gender": person.get("gender", ""),
                "preferred_language": preferences.get("preferred_language", ""),
                "learning_mode": preferences.get("learning_mode", ""),
                "interests": ", ".join(preferences.get("interests", [])),
                "highest_academic_level": academic_background.get(
                    "highest_academic_level", ""
                ),
                "fields_of_study": ", ".join(
                    [
                        field.get("field_name", "")
                        for field in academic_background.get("fields_of_study", [])
                    ]
                ),
                "institution": ", ".join(
                    [
                        field.get("institution", "")
                        for field in academic_background.get("fields_of_study", [])
                    ]
                ),
                "year_of_completion": ", ".join(
                    [
                        str(field.get("year_of_completion", ""))
                        for field in academic_background.get("fields_of_study", [])
                    ]
                ),
                "total_experience_years": professional_background.get(
                    "total_experience_years", ""
                ),
                "jobs": ", ".join(
                    [
                        job.get("title", "")
                        for job in professional_background.get("jobs", [])
                    ]
                ),
                "short_term_goals": ", ".join(goals.get("short_term_goals", [])),
                "long_term_goals": ", ".join(goals.get("long_term_goals", [])),
            }
        )

    # Convertir en DataFrame Pandas
    df = pd.DataFrame(processed_data)

    # Sauvegarder en CSV
    df.to_csv(csv_file_path, index=False, encoding="utf-8")
    print(f"Les données ont été converties et sauvegardées dans {csv_file_path}")


# Exemple d'utilisation
json_file_path = (
    "generated_student_data.json"  # Remplacez par le chemin de votre fichier JSON
)
csv_file_path = "generated_student_data.csv"  # Chemin pour sauvegarder le fichier CSV
convert_json_to_csv(json_file_path, csv_file_path)
