import random
import json
from faker import Faker
import pandas as pd 

fake = Faker("fr_FR")  # Localisation française

# Données prédéfinies
languages = ["français", "anglais", ""]
learning_modes = ["en ligne", "présentiel", "mixte"]
interests = ["Data Scientist", "Data Engineer", "Devops", "Infrastructures & Sécurité"]
fields_of_study = ["Informatique", "", "", "", ""]
positions = ["Analyste", "Développeur", "Chef de projet", "Cyber Sécurité", "Consultant"]
companies = ["TechCorp", "InnoSolutions", "DataAnalytics", "", ""]

# Fonction pour générer les données d'un utilisateur
def generer_donnees():
    return {
        "personne": {  # Clé en français
            "id": fake.uuid4(),
            "nom": f"{fake.first_name()} {fake.last_name()}",
            "âge": random.randint(18, 60),
            "sexe": random.choice(["Homme", "Femme"]),
            "contact": {
                "email": fake.email(),
                "téléphone": fake.phone_number(),
            },
        },
        "préférences": {
            "langue_préférée": random.choice(languages),
            "mode_d_apprentissage": random.choice(learning_modes),
            "centres_d_intérêt": random.sample(interests, random.randint(1, 3)),
        },
        "parcours_académique": {
            "niveau_académique_le_plus_élevé": random.choice(["licence", "master", "doctorat"]),
            "domaines_d_étude": [
                {
                    "domaine": random.choice(fields_of_study),
                    "institution": fake.company(),
                    "année_de_fin": random.randint(2000, 2023),
                }
                for _ in range(random.randint(1, 3))
            ],
        },
        "parcours_professionnel": {
            "années_d_expérience": random.randint(0, 15),
            "emplois": [
                {
                    "poste": random.choice(positions),
                    "entreprise": random.choice(companies),
                    "date_début": fake.date_between(start_date="-15y", end_date="today").isoformat(),
                    "date_fin": random.choice(
                        [fake.date_between(start_date="-5y", end_date="today").isoformat(), "actuel"]
                    ),
                    "description": fake.sentence(nb_words=10),  # Pas besoin de locale ici
                }
                for _ in range(random.randint(1, 5))
            ],
        },
        "objectifs": {
            "objectifs_à_court_terme": [
                fake.sentence(nb_words=5) for _ in range(random.randint(1, 3))
            ],
            "objectifs_à_long_terme": [
                fake.sentence(nb_words=8) for _ in range(random.randint(1, 3))
            ],
        },
    }

# Fonction pour générer plusieurs utilisateurs
def generer_donnees_multiples(nb_utilisateurs):
    return [generer_donnees() for _ in range(nb_utilisateurs)]

# Enregistrer les données dans un fichier JSON
def exporter_donnees_json(nom_fichier, donnees):
    with open(nom_fichier, "w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, indent=4, ensure_ascii=False)
        
# Enregistrer les données dans un fichier Excel
def exporter_donnees_excel(nom_fichier, donnees):
    # Mise à plat des données pour le format Excel
    data_flat = [
        {
            "Nom": utilisateur["personne"]["nom"],
            "Âge": utilisateur["personne"]["âge"],
            "Sexe": utilisateur["personne"]["sexe"],
            "Email": utilisateur["personne"]["contact"]["email"],
            "Téléphone": utilisateur["personne"]["contact"]["téléphone"],
            "Langue préférée": utilisateur["préférences"]["langue_préférée"],
            "Mode d'apprentissage": utilisateur["préférences"]["mode_d_apprentissage"],
            "Centres d'intérêt": ", ".join(utilisateur["préférences"]["centres_d_intérêt"]),
            "Niveau académique": utilisateur["parcours_académique"]["niveau_académique_le_plus_élevé"],
            "Expérience (années)": utilisateur["parcours_professionnel"]["années_d_expérience"],
        }
        for utilisateur in donnees
    ]
    df = pd.DataFrame(data_flat)
    df.to_excel(nom_fichier, index=False, sheet_name="Utilisateurs")

# Générer et exporter les données
donnees_utilisateurs = generer_donnees_multiples(100)
#exporter_donnees_json("donnees_utilisateurs_fr.json", donnees_utilisateurs)
exporter_donnees_excel("donnees_utilisateurs_fr.xlsx", donnees_utilisateurs)

#print("Données générées et exportées avec succès dans 'donnees_utilisateurs_fr.json' et 'donnees_utilisateurs_fr.xlsx'.")
