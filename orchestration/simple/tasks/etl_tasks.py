#!/usr/bin/env python3
"""
Tâches ETL pour l'orchestration simple
"""

import pandas as pd
import psycopg2
import logging
from datetime import datetime
import os
import json
import sys

logger = logging.getLogger(__name__)


def run_etl_users_daily():
    """ETL quotidien des utilisateurs depuis Excel vers PostgreSQL"""
    try:
        logger.info("Démarrage de l'ETL quotidien des utilisateurs")

        # Configuration de la base de données
        db_config = {
            "host": os.getenv("POSTGRES_HOST", "localhost"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "database": os.getenv("POSTGRES_DB", "elearning_db"),
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "password"),
        }

        # Chemin vers le fichier Excel
        excel_file = "ETL_users/data.xlsx"

        if not os.path.exists(excel_file):
            logger.warning(f"Fichier Excel non trouvé: {excel_file}")
            return False

        # Lecture du fichier Excel
        df = pd.read_excel(excel_file)
        logger.info(f"Fichier Excel lu: {len(df)} lignes")

        # Transformation des données
        df_clean = df.dropna()
        df_clean["created_at"] = datetime.now()
        df_clean["updated_at"] = datetime.now()

        # Connexion à la base de données
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Insertion des données
        for _, row in df_clean.iterrows():
            try:
                cursor.execute(
                    """
                    INSERT INTO users_person (age, gender, highest_academic_level, 
                                            fields_of_study, professional_experience,
                                            preferred_language, learning_mode, interests,
                                            created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """,
                    (
                        row.get("age"),
                        row.get("gender"),
                        row.get("highest_academic_level"),
                        row.get("fields_of_study"),
                        row.get("professional_experience"),
                        row.get("preferred_language"),
                        row.get("learning_mode"),
                        row.get("interests"),
                        row["created_at"],
                        row["updated_at"],
                    ),
                )
            except Exception as e:
                logger.error(f"Erreur insertion ligne: {e}")
                continue

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"ETL terminé: {len(df_clean)} utilisateurs traités")
        return True

    except Exception as e:
        logger.error(f"Erreur dans l'ETL quotidien: {e}")
        return False


def run_etl_courses_batch():
    """ETL par lot des cours depuis JSON vers Elasticsearch"""
    try:
        logger.info("Démarrage de l'ETL par lot des cours")

        # Import du service Elasticsearch
        sys.path.append("../../elearning/services")
        from elasticsearch_service import elasticsearch_service

        # Chemin vers les fichiers de cours
        courses_dir = "ingest/processed"

        if not os.path.exists(courses_dir):
            logger.warning(f"Dossier des cours non trouvé: {courses_dir}")
            return False

        processed_count = 0

        # Traitement de chaque fichier JSON
        for filename in os.listdir(courses_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(courses_dir, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        courses_data = json.load(f)

                    # Insertion dans Elasticsearch
                    for course in courses_data:
                        elasticsearch_service.index_course(course)
                        processed_count += 1

                    logger.info(f"Fichier {filename} traité: {len(courses_data)} cours")

                except Exception as e:
                    logger.error(f"Erreur traitement fichier {filename}: {e}")
                    continue

        logger.info(f"ETL cours terminé: {processed_count} cours traités")
        return True

    except Exception as e:
        logger.error(f"Erreur dans l'ETL cours: {e}")
        return False
