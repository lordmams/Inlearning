import json
import pandas as pd
import numpy as np
from collections import Counter
import warnings

warnings.filterwarnings("ignore")


class AnalyseDonneesCours:
    def __init__(self, json_file_path):
        """Initialise l'analyse avec le fichier JSON des cours"""
        self.json_file_path = json_file_path
        self.courses_data = self.charger_donnees()
        self.df = self.convertir_en_dataframe()

    def charger_donnees(self):
        """Charge les données JSON des cours"""
        print("Chargement des données des cours...")
        with open(self.json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"✓ {len(data)} cours chargés")
        return data

    def convertir_en_dataframe(self):
        """Convertit les données JSON en DataFrame pandas"""
        print("Conversion en DataFrame...")

        # Extraction des champs principaux
        courses_list = []
        for course in self.courses_data:
            course_info = {
                "titre": course.get("titre", ""),
                "description": course.get("description", ""),
                "niveau": course.get("niveau", 0),
                "categorie": course.get("categorie", ""),
                "score_categorie": course.get("score_categorie", 0.0),
                "url": course.get("url", ""),
                "langage": course.get("langage", ""),
                "difficulte": course.get("difficulte", ""),
                "duree": course.get("duree", ""),
                "instructeur": course.get("instructeur", ""),
                "prix": course.get("prix", 0.0),
                "gratuit": course.get("gratuit", False),
                "note": course.get("note", 0.0),
                "nb_etudiants": course.get("nb_etudiants", 0),
                "nb_avis": course.get("nb_avis", 0),
            }

            # Extraction des probabilités de niveau
            probas = course.get("probabilites_niveau", {})
            for i in range(1, 6):  # Niveaux 1 à 5
                course_info[f"prob_niveau_{i}"] = probas.get(f"niveau_{i}", 0.0)

            courses_list.append(course_info)

        df = pd.DataFrame(courses_list)
        print(f"✓ DataFrame créé avec {len(df)} cours et {len(df.columns)} colonnes")
        return df

    def analyse_generale(self):
        """Analyse générale des données"""
        print("=" * 60)
        print("ANALYSE GÉNÉRALE")
        print("=" * 60)

        print(f"Nombre total de cours : {len(self.df)}")
        print(f"Nombre de colonnes : {len(self.df.columns)}")
        print(f"Période de données : {self.df.columns.tolist()}")

        # Statistiques sur les niveaux
        print(f"\nStatistiques des niveaux :")
        print(f"  Niveau moyen : {self.df['niveau'].mean():.2f}")
        print(f"  Niveau médian : {self.df['niveau'].median():.2f}")
        print(f"  Écart-type : {self.df['niveau'].std():.2f}")
        print(f"  Niveau minimum : {self.df['niveau'].min()}")
        print(f"  Niveau maximum : {self.df['niveau'].max()}")

        # Distribution des niveaux
        print(f"\nDistribution des niveaux :")
        niveau_dist = self.df["niveau"].value_counts().sort_index()
        for niveau, count in niveau_dist.items():
            percentage = (count / len(self.df)) * 100
            print(f"  Niveau {niveau} : {count} cours ({percentage:.1f}%)")

    def analyse_categories(self):
        """Analyse des catégories de cours"""
        print("\n" + "=" * 60)
        print("ANALYSE DES CATÉGORIES")
        print("=" * 60)

        # Top 20 des catégories
        cat_dist = self.df["categorie"].value_counts().head(20)
        print("Top 20 des catégories de cours :")
        for cat, count in cat_dist.items():
            percentage = (count / len(self.df)) * 100
            print(f"  {cat} : {count} cours ({percentage:.1f}%)")

        # Analyse des scores de catégorie
        print(f"\nStatistiques des scores de catégorie :")
        print(f"  Score moyen : {self.df['score_categorie'].mean():.3f}")
        print(f"  Score médian : {self.df['score_categorie'].median():.3f}")
        print(f"  Score minimum : {self.df['score_categorie'].min():.3f}")
        print(f"  Score maximum : {self.df['score_categorie'].max():.3f}")

        # Cours avec score élevé
        high_score_courses = self.df[self.df["score_categorie"] > 0.8]
        print(
            f"\nCours avec score de catégorie > 0.8 : {len(high_score_courses)} ({len(high_score_courses)/len(self.df)*100:.1f}%)"
        )

    def analyse_langages(self):
        """Analyse des langages de programmation"""
        print("\n" + "=" * 60)
        print("ANALYSE DES LANGAGES")
        print("=" * 60)

        # Top 15 des langages
        lang_dist = self.df["langage"].value_counts().head(15)
        print("Top 15 des langages de programmation :")
        for lang, count in lang_dist.items():
            percentage = (count / len(self.df)) * 100
            print(f"  {lang} : {count} cours ({percentage:.1f}%)")

        # Analyse par langage et niveau
        print(f"\nRépartition des niveaux par langage (top 10) :")
        top_langages = self.df["langage"].value_counts().head(10).index

        for lang in top_langages:
            lang_courses = self.df[self.df["langage"] == lang]
            print(f"\n  {lang} ({len(lang_courses)} cours) :")
            niveau_dist = lang_courses["niveau"].value_counts().sort_index()
            for niveau, count in niveau_dist.items():
                percentage = (count / len(lang_courses)) * 100
                print(f"    Niveau {niveau} : {count} cours ({percentage:.1f}%)")

    def analyse_difficulte(self):
        """Analyse des niveaux de difficulté"""
        print("\n" + "=" * 60)
        print("ANALYSE DES NIVEAUX DE DIFFICULTÉ")
        print("=" * 60)

        # Distribution des difficultés
        diff_dist = self.df["difficulte"].value_counts()
        print("Distribution des niveaux de difficulté :")
        for diff, count in diff_dist.items():
            percentage = (count / len(self.df)) * 100
            print(f"  {diff} : {count} cours ({percentage:.1f}%)")

        # Corrélation difficulté vs niveau
        if "difficulte" in self.df.columns and "niveau" in self.df.columns:
            # Créer un mapping de difficulté vers niveau numérique
            diff_mapping = {
                "Débutant": 1,
                "Intermédiaire": 3,
                "Avancé": 5,
                "débutant": 1,
                "intermédiaire": 3,
                "avancé": 5,
            }

            self.df["difficulte_num"] = self.df["difficulte"].map(diff_mapping)
            correlation = self.df["difficulte_num"].corr(self.df["niveau"])
            print(f"\nCorrélation difficulté vs niveau : {correlation:.3f}")

    def analyse_prix(self):
        """Analyse des prix des cours"""
        print("\n" + "=" * 60)
        print("ANALYSE DES PRIX")
        print("=" * 60)

        # Statistiques des prix
        prix_data = self.df[self.df["prix"] > 0]  # Cours payants uniquement
        print(
            f"Cours payants : {len(prix_data)} ({len(prix_data)/len(self.df)*100:.1f}%)"
        )
        print(
            f"Cours gratuits : {len(self.df) - len(prix_data)} ({(len(self.df) - len(prix_data))/len(self.df)*100:.1f}%)"
        )

        if len(prix_data) > 0:
            print(f"\nStatistiques des prix (cours payants) :")
            print(f"  Prix moyen : {prix_data['prix'].mean():.2f} €")
            print(f"  Prix médian : {prix_data['prix'].median():.2f} €")
            print(f"  Prix minimum : {prix_data['prix'].min():.2f} €")
            print(f"  Prix maximum : {prix_data['prix'].max():.2f} €")

            # Distribution des prix
            prix_bins = [0, 10, 20, 50, 100, 200, 1000]
            prix_labels = ["0-10€", "10-20€", "20-50€", "50-100€", "100-200€", "200€+"]
            prix_data["prix_group"] = pd.cut(
                prix_data["prix"], bins=prix_bins, labels=prix_labels, right=False
            )
            prix_dist = prix_data["prix_group"].value_counts().sort_index()

            print(f"\nDistribution des prix :")
            for prix_group, count in prix_dist.items():
                percentage = (count / len(prix_data)) * 100
                print(f"  {prix_group} : {count} cours ({percentage:.1f}%)")

    def analyse_notes(self):
        """Analyse des notes et évaluations"""
        print("\n" + "=" * 60)
        print("ANALYSE DES NOTES ET ÉVALUATIONS")
        print("=" * 60)

        # Statistiques des notes
        notes_data = self.df[self.df["note"] > 0]  # Cours avec notes
        print(
            f"Cours avec notes : {len(notes_data)} ({len(notes_data)/len(self.df)*100:.1f}%)"
        )

        if len(notes_data) > 0:
            print(f"\nStatistiques des notes :")
            print(f"  Note moyenne : {notes_data['note'].mean():.2f}/5")
            print(f"  Note médiane : {notes_data['note'].median():.2f}/5")
            print(f"  Note minimum : {notes_data['note'].min():.2f}/5")
            print(f"  Note maximum : {notes_data['note'].max():.2f}/5")

            # Distribution des notes
            note_bins = [0, 3, 3.5, 4, 4.5, 5]
            note_labels = ["<3", "3-3.5", "3.5-4", "4-4.5", "4.5-5"]
            notes_data["note_group"] = pd.cut(
                notes_data["note"], bins=note_bins, labels=note_labels, right=False
            )
            note_dist = notes_data["note_group"].value_counts().sort_index()

            print(f"\nDistribution des notes :")
            for note_group, count in note_dist.items():
                percentage = (count / len(notes_data)) * 100
                print(f"  {note_group} : {count} cours ({percentage:.1f}%)")

        # Analyse du nombre d'étudiants
        etudiants_data = self.df[self.df["nb_etudiants"] > 0]
        print(
            f"\nCours avec nombre d'étudiants : {len(etudiants_data)} ({len(etudiants_data)/len(self.df)*100:.1f}%)"
        )

        if len(etudiants_data) > 0:
            print(
                f"  Nombre moyen d'étudiants : {etudiants_data['nb_etudiants'].mean():.0f}"
            )
            print(
                f"  Nombre médian d'étudiants : {etudiants_data['nb_etudiants'].median():.0f}"
            )
            print(
                f"  Nombre maximum d'étudiants : {etudiants_data['nb_etudiants'].max():.0f}"
            )

    def analyse_probabilites_niveau(self):
        """Analyse des probabilités de niveau"""
        print("\n" + "=" * 60)
        print("ANALYSE DES PROBABILITÉS DE NIVEAU")
        print("=" * 60)

        # Moyennes des probabilités par niveau
        prob_cols = [col for col in self.df.columns if col.startswith("prob_niveau_")]

        if prob_cols:
            print("Moyennes des probabilités par niveau :")
            for col in prob_cols:
                niveau = col.split("_")[-1]
                moyenne = self.df[col].mean()
                print(f"  Niveau {niveau} : {moyenne:.3f}")

            # Cours avec forte certitude de niveau
            print(f"\nAnalyse de la certitude des niveaux :")
            for col in prob_cols:
                niveau = col.split("_")[-1]
                certitude_elevee = self.df[self.df[col] > 0.8]
                print(
                    f"  Niveau {niveau} avec certitude >80% : {len(certitude_elevee)} cours"
                )

    def analyse_correlations(self):
        """Analyse des corrélations entre variables"""
        print("\n" + "=" * 60)
        print("ANALYSE DES CORRÉLATIONS")
        print("=" * 60)

        # Variables numériques
        numeric_cols = [
            "niveau",
            "score_categorie",
            "prix",
            "note",
            "nb_etudiants",
            "nb_avis",
        ]
        numeric_df = self.df[numeric_cols].select_dtypes(include=[np.number])

        if len(numeric_df.columns) > 1:
            correlations = numeric_df.corr()

            print("Matrice de corrélation (variables numériques) :")
            for i, col1 in enumerate(numeric_df.columns):
                for j, col2 in enumerate(numeric_df.columns):
                    if i < j:  # Éviter les doublons
                        corr = correlations.loc[col1, col2]
                        if (
                            abs(corr) > 0.1
                        ):  # Afficher seulement les corrélations significatives
                            print(f"  {col1} vs {col2} : {corr:.3f}")

    def analyse_qualite_donnees(self):
        """Analyse de la qualité des données"""
        print("\n" + "=" * 60)
        print("ANALYSE DE LA QUALITÉ DES DONNÉES")
        print("=" * 60)

        # Valeurs manquantes
        missing_data = self.df.isnull().sum()
        missing_percent = (missing_data / len(self.df)) * 100

        print("Valeurs manquantes par colonne :")
        for col in self.df.columns:
            if missing_data[col] > 0:
                print(f"  {col} : {missing_data[col]} ({missing_percent[col]:.1f}%)")

        # Cours avec données complètes
        complete_courses = self.df.dropna()
        print(
            f"\nCours avec données complètes : {len(complete_courses)} ({len(complete_courses)/len(self.df)*100:.1f}%)"
        )

        # Longueur des descriptions
        self.df["desc_length"] = self.df["description"].str.len()
        print(f"\nStatistiques des descriptions :")
        print(f"  Longueur moyenne : {self.df['desc_length'].mean():.0f} caractères")
        print(f"  Longueur médiane : {self.df['desc_length'].median():.0f} caractères")
        print(f"  Longueur minimum : {self.df['desc_length'].min():.0f} caractères")
        print(f"  Longueur maximum : {self.df['desc_length'].max():.0f} caractères")

    def top_cours_par_categorie(self):
        """Affiche les meilleurs cours par catégorie"""
        print("\n" + "=" * 60)
        print("MEILLEURS COURS PAR CATÉGORIE")
        print("=" * 60)

        # Top 5 catégories
        top_categories = self.df["categorie"].value_counts().head(5).index

        for cat in top_categories:
            cat_courses = self.df[self.df["categorie"] == cat]

            # Meilleurs cours par note
            if "note" in cat_courses.columns and cat_courses["note"].max() > 0:
                best_courses = cat_courses.nlargest(3, "note")
                print(f"\n{cat} - Meilleurs cours par note :")
                for _, course in best_courses.iterrows():
                    print(
                        f"  • {course['titre'][:50]}... (Note: {course['note']:.1f}/5)"
                    )

            # Cours les plus populaires
            if (
                "nb_etudiants" in cat_courses.columns
                and cat_courses["nb_etudiants"].max() > 0
            ):
                popular_courses = cat_courses.nlargest(3, "nb_etudiants")
                print(f"\n{cat} - Cours les plus populaires :")
                for _, course in popular_courses.iterrows():
                    print(
                        f"  • {course['titre'][:50]}... ({course['nb_etudiants']:.0f} étudiants)"
                    )

    def analyse_complete(self):
        """Lance l'analyse complète des données"""
        print("ANALYSE COMPLÈTE DES DONNÉES DE COURS")
        print("=" * 80)

        self.analyse_generale()
        self.analyse_categories()
        self.analyse_langages()
        self.analyse_difficulte()
        self.analyse_prix()
        self.analyse_notes()
        self.analyse_probabilites_niveau()
        self.analyse_correlations()
        self.analyse_qualite_donnees()
        self.top_cours_par_categorie()

        print("\n" + "=" * 80)
        print("ANALYSE TERMINÉE")
        print("=" * 80)


# Exécution de l'analyse
if __name__ == "__main__":
    # Chemin vers le fichier JSON
    json_file = "merged_courses_cleaned.json"

    # Création de l'instance d'analyse
    analyseur = AnalyseDonneesCours(json_file)

    # Lancement de l'analyse complète
    analyseur.analyse_complete()
