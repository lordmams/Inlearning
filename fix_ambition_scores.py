#!/usr/bin/env python3
"""
Script pour corriger le problème d'ambition dans le dataset des étudiants.
Génère des objectifs variés pour créer des scores d'ambition réalistes.
"""

import pandas as pd
import numpy as np
import random
from collections import Counter


def generate_varied_goals():
    """Génère des objectifs variés pour créer des scores d'ambition réalistes."""

    # Objectifs court terme variés
    short_term_goals = [
        "Apprendre Python",
        "Maîtriser Docker",
        "Stage en entreprise",
        "Certification AWS",
        "Projet personnel",
        "Formation DevOps",
        "Apprendre React",
        "Certification Azure",
        "Bootcamp intensif",
        "Formation Data Science",
        "Apprendre Kubernetes",
        "Certification GCP",
        "Projet open source",
        "Formation cybersécurité",
        "Apprendre Node.js",
        "Certification Scrum",
        "Formation IA",
        "Apprendre Vue.js",
        "Stage développement",
        "Formation cloud",
        "Apprendre Angular",
        "Certification PMP",
        "Projet freelance",
        "Formation blockchain",
        "Apprendre Flutter",
        "Certification ITIL",
        "Formation mobile",
        "Apprendre Rust",
        "Certification CISSP",
        "Formation web3",
    ]

    # Objectifs long terme variés
    long_term_goals = [
        "Architecte Cloud",
        "Créer une startup",
        "Spécialisation Big Data",
        "Freelance",
        "Lead Developer",
        "Data Scientist",
        "Reconvertion en développement",
        "CTO",
        "Expert IA",
        "Consultant indépendant",
        "Product Manager",
        "DevOps Engineer",
        "Spécialisation cybersécurité",
        "Créer une entreprise",
        "Tech Lead",
        "Expert Blockchain",
        "Manager technique",
        "Spécialisation mobile",
        "Créer une agence",
        "Expert Cloud",
        "Spécialisation web3",
        "Directeur technique",
        "Expert Data",
        "Spécialisation DevOps",
        "Créer une plateforme",
        "Expert Sécurité",
        "Spécialisation IA",
        "Consultant senior",
        "Expert Mobile",
        "Spécialisation Cloud",
    ]

    return short_term_goals, long_term_goals


def create_varied_ambition_scores(df):
    """Crée des scores d'ambition variés basés sur les caractéristiques des étudiants."""

    short_term_goals, long_term_goals = generate_varied_goals()

    # Facteurs qui influencent l'ambition
    ambition_factors = {
        "age": lambda x: (
            1.2 if x < 25 else 1.0 if x < 35 else 0.8
        ),  # Plus ambitieux quand jeune
        "total_experience_years": lambda x: (
            1.1 if x < 5 else 1.0 if x < 15 else 0.9
        ),  # Moins d'exp = plus ambitieux
        "highest_academic_level": {
            "Baccalauréat": 1.3,
            "Bac+2": 1.2,
            "Bac+3": 1.1,
            "Bac+5": 1.0,
            "Bac+8": 0.9,
        },
    }

    new_short_goals = []
    new_long_goals = []

    for idx, row in df.iterrows():
        # Calcul du facteur d'ambition pour cet étudiant
        age_factor = ambition_factors["age"](row["age"])
        exp_factor = ambition_factors["total_experience_years"](
            row["total_experience_years"]
        )
        academic_factor = ambition_factors["highest_academic_level"].get(
            row["highest_academic_level"], 1.0
        )

        # Score d'ambition de base (1-5)
        base_ambition = np.random.normal(3, 1)  # Distribution normale autour de 3
        ambition_score = base_ambition * age_factor * exp_factor * academic_factor
        ambition_score = max(1, min(5, ambition_score))  # Limiter entre 1 et 5

        # Déterminer le nombre d'objectifs
        nb_short = max(1, min(3, int(ambition_score)))
        nb_long = max(1, min(3, int(ambition_score * 0.8)))

        # Sélectionner des objectifs aléatoires
        selected_short = random.sample(short_term_goals, nb_short)
        selected_long = random.sample(long_term_goals, nb_long)

        new_short_goals.append(", ".join(selected_short))
        new_long_goals.append(", ".join(selected_long))

    return new_short_goals, new_long_goals


def main():
    """Fonction principale pour corriger le dataset."""

    print("🔧 Correction du problème d'ambition dans le dataset...")

    # Charger le dataset
    input_file = "LLM/generated_student_data_100k_final.csv"
    output_file = "LLM/generated_student_data_100k_fixed.csv"

    print(f"📖 Chargement du fichier: {input_file}")
    df = pd.read_csv(input_file)

    print(f"📊 Dataset chargé: {len(df):,} étudiants")

    # Analyser l'état actuel
    print("\n🔍 Analyse de l'état actuel:")

    # Fonction pour parser les listes
    def parse_list_string(text):
        if pd.isna(text):
            return []
        items = [item.strip().strip("\"'") for item in str(text).split(",")]
        return [item for item in items if item]

    # Analyser les objectifs actuels
    df["short_goals_list"] = df["short_term_goals"].apply(parse_list_string)
    df["long_goals_list"] = df["long_term_goals"].apply(parse_list_string)

    current_short_counts = [len(goals) for goals in df["short_goals_list"]]
    current_long_counts = [len(goals) for goals in df["long_goals_list"]]
    current_ambition_scores = [
        s + l for s, l in zip(current_short_counts, current_long_counts)
    ]

    print(
        f"   • Score d'ambition actuel: {np.mean(current_ambition_scores):.1f} ± {np.std(current_ambition_scores):.1f}"
    )
    print(
        f"   • Objectifs court terme: {np.mean(current_short_counts):.1f} ± {np.std(current_short_counts):.1f}"
    )
    print(
        f"   • Objectifs long terme: {np.mean(current_long_counts):.1f} ± {np.std(current_long_counts):.1f}"
    )

    # Vérifier si tous les scores sont identiques
    if len(set(current_ambition_scores)) == 1:
        print("   ⚠️  PROBLÈME DÉTECTÉ: Tous les scores d'ambition sont identiques!")
    else:
        print("   ✅ Scores d'ambition variés détectés")

    # Générer de nouveaux objectifs variés
    print("\n🎯 Génération de nouveaux objectifs variés...")
    new_short_goals, new_long_goals = create_varied_ambition_scores(df)

    # Mettre à jour le dataset
    df["short_term_goals"] = new_short_goals
    df["long_term_goals"] = new_long_goals

    # Analyser les nouveaux scores
    df["short_goals_list"] = df["short_term_goals"].apply(parse_list_string)
    df["long_goals_list"] = df["long_term_goals"].apply(parse_list_string)

    new_short_counts = [len(goals) for goals in df["short_goals_list"]]
    new_long_counts = [len(goals) for goals in df["long_goals_list"]]
    new_ambition_scores = [s + l for s, l in zip(new_short_counts, new_long_counts)]

    print("\n📈 Nouveaux scores d'ambition:")
    print(
        f"   • Score d'ambition moyen: {np.mean(new_ambition_scores):.1f} ± {np.std(new_ambition_scores):.1f}"
    )
    print(
        f"   • Objectifs court terme: {np.mean(new_short_counts):.1f} ± {np.std(new_short_counts):.1f}"
    )
    print(
        f"   • Objectifs long terme: {np.mean(new_long_counts):.1f} ± {np.std(new_long_counts):.1f}"
    )
    print(f"   • Distribution: {dict(Counter(new_ambition_scores))}")

    # Sauvegarder le dataset corrigé
    print(f"\n💾 Sauvegarde du dataset corrigé: {output_file}")
    df.to_csv(output_file, index=False)

    # Nettoyer les colonnes temporaires
    df = df.drop(["short_goals_list", "long_goals_list"], axis=1)

    print("\n✅ CORRECTION TERMINÉE!")
    print(f"   • Fichier original: {input_file}")
    print(f"   • Fichier corrigé: {output_file}")
    print(f"   • {len(df):,} étudiants traités")

    # Afficher quelques exemples
    print("\n📋 Exemples d'objectifs générés:")
    for i in range(5):
        print(f"   Étudiant {i+1}:")
        print(f"     Court terme: {df.iloc[i]['short_term_goals']}")
        print(f"     Long terme: {df.iloc[i]['long_term_goals']}")
        print()


if __name__ == "__main__":
    main()
