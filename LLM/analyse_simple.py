import pandas as pd
import numpy as np
from collections import Counter
import json


class AnalyseSimpleDonneesEtudiants:
    def __init__(self, csv_file_path):
        """Initialise l'analyse avec le fichier CSV des données d'étudiants"""
        self.df = pd.read_csv(csv_file_path)
        self.df_clean = self.nettoyer_donnees()

    def nettoyer_donnees(self):
        """Nettoie et prépare les données pour l'analyse"""
        df = self.df.copy()

        # Conversion des types de données
        df["age"] = pd.to_numeric(df["age"], errors="coerce")
        df["total_experience_years"] = pd.to_numeric(
            df["total_experience_years"], errors="coerce"
        )

        # Nettoyage des langages préférés
        df["preferred_language"] = df["preferred_language"].str.strip()

        # Nettoyage des modes d'apprentissage
        df["learning_mode"] = df["learning_mode"].str.strip()

        # Nettoyage des niveaux académiques
        df["highest_academic_level"] = df["highest_academic_level"].str.strip()

        return df

    def analyse_demographique(self):
        """Analyse démographique des étudiants"""
        print("=" * 60)
        print("ANALYSE DÉMOGRAPHIQUE")
        print("=" * 60)

        # Statistiques de base
        print(f"Nombre total d'étudiants : {len(self.df_clean)}")
        print(f"Âge moyen : {self.df_clean['age'].mean():.1f} ans")
        print(f"Âge médian : {self.df_clean['age'].median():.1f} ans")
        print(f"Écart-type de l'âge : {self.df_clean['age'].std():.1f} ans")
        print(f"Âge minimum : {self.df_clean['age'].min():.0f} ans")
        print(f"Âge maximum : {self.df_clean['age'].max():.0f} ans")

        # Distribution par genre
        print(f"\nDistribution par genre :")
        gender_dist = self.df_clean["gender"].value_counts()
        for gender, count in gender_dist.items():
            percentage = (count / len(self.df_clean)) * 100
            print(f"  {gender} : {count} ({percentage:.1f}%)")

        # Distribution par âge
        print(f"\nDistribution par tranche d'âge :")
        age_bins = [18, 25, 30, 35, 40, 50, 100]
        age_labels = ["18-25", "26-30", "31-35", "36-40", "41-50", "50+"]
        self.df_clean["age_group"] = pd.cut(
            self.df_clean["age"], bins=age_bins, labels=age_labels, right=False
        )
        age_dist = self.df_clean["age_group"].value_counts().sort_index()
        for age_group, count in age_dist.items():
            percentage = (count / len(self.df_clean)) * 100
            print(f"  {age_group} : {count} ({percentage:.1f}%)")

    def analyse_langages_preferes(self):
        """Analyse des langages de programmation préférés"""
        print("\n" + "=" * 60)
        print("ANALYSE DES LANGAGES PRÉFÉRÉS")
        print("=" * 60)

        # Top 15 des langages préférés
        lang_dist = self.df_clean["preferred_language"].value_counts().head(15)
        print("Top 15 des langages de programmation préférés :")
        for lang, count in lang_dist.items():
            percentage = (count / len(self.df_clean)) * 100
            print(f"  {lang} : {count} ({percentage:.1f}%)")

    def analyse_modes_apprentissage(self):
        """Analyse des modes d'apprentissage préférés"""
        print("\n" + "=" * 60)
        print("ANALYSE DES MODES D'APPRENTISSAGE")
        print("=" * 60)

        # Distribution des modes d'apprentissage
        mode_dist = self.df_clean["learning_mode"].value_counts()
        print("Distribution des modes d'apprentissage :")
        for mode, count in mode_dist.items():
            percentage = (count / len(self.df_clean)) * 100
            print(f"  {mode} : {count} ({percentage:.1f}%)")

    def analyse_niveaux_academiques(self):
        """Analyse des niveaux académiques"""
        print("\n" + "=" * 60)
        print("ANALYSE DES NIVEAUX ACADÉMIQUES")
        print("=" * 60)

        # Distribution des niveaux académiques
        level_dist = self.df_clean["highest_academic_level"].value_counts()
        print("Distribution des niveaux académiques :")
        for level, count in level_dist.items():
            percentage = (count / len(self.df_clean)) * 100
            print(f"  {level} : {count} ({percentage:.1f}%)")

    def analyse_experience_professionnelle(self):
        """Analyse de l'expérience professionnelle"""
        print("\n" + "=" * 60)
        print("ANALYSE DE L'EXPÉRIENCE PROFESSIONNELLE")
        print("=" * 60)

        # Statistiques de l'expérience
        print(
            f"Expérience moyenne : {self.df_clean['total_experience_years'].mean():.1f} ans"
        )
        print(
            f"Expérience médiane : {self.df_clean['total_experience_years'].median():.1f} ans"
        )
        print(
            f"Écart-type de l'expérience : {self.df_clean['total_experience_years'].std():.1f} ans"
        )
        print(
            f"Expérience minimum : {self.df_clean['total_experience_years'].min():.0f} ans"
        )
        print(
            f"Expérience maximum : {self.df_clean['total_experience_years'].max():.0f} ans"
        )

        # Distribution par tranche d'expérience
        exp_bins = [0, 1, 3, 5, 10, 15, 30]
        exp_labels = [
            "0-1 an",
            "1-3 ans",
            "3-5 ans",
            "5-10 ans",
            "10-15 ans",
            "15+ ans",
        ]
        self.df_clean["exp_group"] = pd.cut(
            self.df_clean["total_experience_years"],
            bins=exp_bins,
            labels=exp_labels,
            right=False,
        )
        exp_dist = self.df_clean["exp_group"].value_counts().sort_index()

        print(f"\nDistribution par tranche d'expérience :")
        for exp_group, count in exp_dist.items():
            percentage = (count / len(self.df_clean)) * 100
            print(f"  {exp_group} : {count} ({percentage:.1f}%)")

    def analyse_correlations(self):
        """Analyse des corrélations entre variables"""
        print("\n" + "=" * 60)
        print("ANALYSE DES CORRÉLATIONS")
        print("=" * 60)

        # Corrélation âge vs expérience
        correlation = self.df_clean["age"].corr(self.df_clean["total_experience_years"])
        print(f"Corrélation entre âge et expérience : {correlation:.3f}")

        if correlation > 0.7:
            print("  → Forte corrélation positive")
        elif correlation > 0.3:
            print("  → Corrélation positive modérée")
        elif correlation > -0.3:
            print("  → Corrélation faible")
        elif correlation > -0.7:
            print("  → Corrélation négative modérée")
        else:
            print("  → Forte corrélation négative")

    def analyse_interets(self):
        """Analyse des centres d'intérêt"""
        print("\n" + "=" * 60)
        print("ANALYSE DES CENTRES D'INTÉRÊT")
        print("=" * 60)

        # Extraction des intérêts
        all_interests = []
        for interests_str in self.df_clean["interests"].dropna():
            interests_list = [interest.strip() for interest in interests_str.split(",")]
            all_interests.extend(interests_list)

        # Comptage des intérêts
        interest_counts = Counter(all_interests)
        top_interests = interest_counts.most_common(20)

        print("Top 20 des centres d'intérêt :")
        for interest, count in top_interests:
            percentage = (count / len(all_interests)) * 100
            print(f"  {interest} : {count} ({percentage:.1f}%)")

    def analyse_objectifs(self):
        """Analyse des objectifs court et long terme"""
        print("\n" + "=" * 60)
        print("ANALYSE DES OBJECTIFS")
        print("=" * 60)

        # Extraction des objectifs court terme
        all_short_goals = []
        for goals_str in self.df_clean["short_term_goals"].dropna():
            goals_list = [goal.strip() for goal in goals_str.split(",")]
            all_short_goals.extend(goals_list)

        # Extraction des objectifs long terme
        all_long_goals = []
        for goals_str in self.df_clean["long_term_goals"].dropna():
            goals_list = [goal.strip() for goal in goals_str.split(",")]
            all_long_goals.extend(goals_list)

        # Top 15 objectifs court terme
        short_goals_counts = Counter(all_short_goals)
        top_short_goals = short_goals_counts.most_common(15)

        print("Top 15 des objectifs court terme :")
        for goal, count in top_short_goals:
            percentage = (count / len(all_short_goals)) * 100
            print(f"  {goal} : {count} ({percentage:.1f}%)")

        # Top 15 objectifs long terme
        long_goals_counts = Counter(all_long_goals)
        top_long_goals = long_goals_counts.most_common(15)

        print(f"\nTop 15 des objectifs long terme :")
        for goal, count in top_long_goals:
            percentage = (count / len(all_long_goals)) * 100
            print(f"  {goal} : {count} ({percentage:.1f}%)")

    def profil_typique(self):
        """Identification du profil typique"""
        print("\n" + "=" * 60)
        print("PROFIL TYPIQUE")
        print("=" * 60)

        # Profil typique basé sur les modes
        typical_profile = {
            "âge_médian": self.df_clean["age"].median(),
            "langage_préféré": self.df_clean["preferred_language"].mode().iloc[0],
            "mode_apprentissage": self.df_clean["learning_mode"].mode().iloc[0],
            "niveau_académique": self.df_clean["highest_academic_level"].mode().iloc[0],
            "expérience_moyenne": self.df_clean["total_experience_years"].mean(),
        }

        print("Profil typique de l'étudiant :")
        print(f"  Âge médian : {typical_profile['âge_médian']:.0f} ans")
        print(f"  Langage préféré : {typical_profile['langage_préféré']}")
        print(f"  Mode d'apprentissage : {typical_profile['mode_apprentissage']}")
        print(f"  Niveau académique : {typical_profile['niveau_académique']}")
        print(f"  Expérience moyenne : {typical_profile['expérience_moyenne']:.1f} ans")

    def analyse_segments(self):
        """Analyse par segments d'utilisateurs"""
        print("\n" + "=" * 60)
        print("ANALYSE PAR SEGMENTS")
        print("=" * 60)

        # Segment par âge
        jeunes = self.df_clean[self.df_clean["age"] <= 25]
        adultes = self.df_clean[
            (self.df_clean["age"] > 25) & (self.df_clean["age"] <= 35)
        ]
        seniors = self.df_clean[self.df_clean["age"] > 35]

        print(
            f"Segment Jeunes (18-25 ans) : {len(jeunes)} personnes ({len(jeunes)/len(self.df_clean)*100:.1f}%)"
        )
        print(f"  Langage préféré : {jeunes['preferred_language'].mode().iloc[0]}")
        print(f"  Mode d'apprentissage : {jeunes['learning_mode'].mode().iloc[0]}")

        print(
            f"\nSegment Adultes (26-35 ans) : {len(adultes)} personnes ({len(adultes)/len(self.df_clean)*100:.1f}%)"
        )
        print(f"  Langage préféré : {adultes['preferred_language'].mode().iloc[0]}")
        print(f"  Mode d'apprentissage : {adultes['learning_mode'].mode().iloc[0]}")

        print(
            f"\nSegment Seniors (35+ ans) : {len(seniors)} personnes ({len(seniors)/len(self.df_clean)*100:.1f}%)"
        )
        print(f"  Langage préféré : {seniors['preferred_language'].mode().iloc[0]}")
        print(f"  Mode d'apprentissage : {seniors['learning_mode'].mode().iloc[0]}")

    def analyse_complete(self):
        """Lance l'analyse complète des données"""
        print("ANALYSE COMPLÈTE DES DONNÉES D'ÉTUDIANTS")
        print("=" * 80)

        self.analyse_demographique()
        self.analyse_langages_preferes()
        self.analyse_modes_apprentissage()
        self.analyse_niveaux_academiques()
        self.analyse_experience_professionnelle()
        self.analyse_correlations()
        self.analyse_interets()
        self.analyse_objectifs()
        self.profil_typique()
        self.analyse_segments()

        print("\n" + "=" * 80)
        print("ANALYSE TERMINÉE")
        print("=" * 80)


# Exécution de l'analyse
if __name__ == "__main__":
    # Chemin vers le fichier CSV
    csv_file = "generated_student_data.csv"

    # Création de l'instance d'analyse
    analyseur = AnalyseSimpleDonneesEtudiants(csv_file)

    # Lancement de l'analyse complète
    analyseur.analyse_complete()
