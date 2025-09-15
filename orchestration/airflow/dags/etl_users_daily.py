"""
DAG ETL Users Daily: Extract-Transform-Load des utilisateurs depuis Excel vers PostgreSQL
Exécution quotidienne à 02:00 AM
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable
import pandas as pd
import os
import logging
import psycopg2.extras

# Configuration par défaut du DAG
default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "start_date": datetime(2025, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "catchup": False,
}

# Définition du DAG
dag = DAG(
    "etl_users_daily",
    default_args=default_args,
    description="ETL quotidien des utilisateurs Excel → PostgreSQL",
    schedule_interval="0 2 * * *",  # Tous les jours à 2h du matin
    max_active_runs=1,
    tags=["etl", "users", "excel", "postgresql", "daily"],
)


def extract_users_from_excel(**context):
    """
    Extraction des données utilisateurs depuis le fichier Excel
    """
    try:
        # Chemin vers le fichier Excel
        excel_file_path = "/opt/airflow/data/ETL_users/data.xlsx"

        logging.info(f"Début de l'extraction depuis {excel_file_path}")

        # Vérification de l'existence du fichier
        if not os.path.exists(excel_file_path):
            raise FileNotFoundError(f"Fichier Excel non trouvé: {excel_file_path}")

        # Lecture du fichier Excel
        df = pd.read_excel(excel_file_path, sheet_name=0)

        logging.info(f"Données extraites: {len(df)} lignes, {len(df.columns)} colonnes")
        logging.info(f"Colonnes disponibles: {list(df.columns)}")

        # Sauvegarde temporaire en CSV pour la prochaine étape
        temp_csv_path = "/tmp/users_extracted.csv"
        df.to_csv(temp_csv_path, index=False)

        # Retour des métadonnées
        return {
            "rows_extracted": len(df),
            "columns": list(df.columns),
            "temp_file": temp_csv_path,
            "extraction_timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logging.error(f"Erreur lors de l'extraction: {str(e)}")
        raise


def transform_users_data(**context):
    """
    Transformation et nettoyage des données utilisateurs
    """
    try:
        # Récupération du chemin du fichier temporaire
        ti = context["ti"]
        extract_info = ti.xcom_pull(task_ids="extract_users")
        temp_file = extract_info["temp_file"]

        logging.info(f"Début de la transformation des données depuis {temp_file}")

        # Lecture des données extraites
        df = pd.read_csv(temp_file)

        # Transformation et nettoyage
        logging.info("Application des transformations...")

        # Standardisation des colonnes
        column_mapping = {
            "Nom": "name",
            "Age": "age",
            "Sexe": "gender",
            "Email": "email",
            "Telephone": "phone",
            "Niveau_predits": "predicted_level",
        }

        # Renommer les colonnes si elles existent
        df = df.rename(
            columns={k: v for k, v in column_mapping.items() if k in df.columns}
        )

        # Nettoyage des données
        # Suppression des lignes vides
        df = df.dropna(subset=["name", "email"])

        # Standardisation du genre
        if "gender" in df.columns:
            df["gender"] = df["gender"].str.lower().str.strip()
            df["gender"] = df["gender"].map(
                {"m": "M", "f": "F", "male": "M", "female": "F"}
            )

        # Validation des emails
        if "email" in df.columns:
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            df = df[df["email"].str.match(email_pattern, na=False)]

        # Validation des âges
        if "age" in df.columns:
            df = df[(df["age"] >= 16) & (df["age"] <= 100)]

        # Ajout de métadonnées
        df["created_at"] = datetime.now()
        df["updated_at"] = datetime.now()
        df["source"] = "excel_etl"

        # Suppression des doublons basés sur l'email
        df = df.drop_duplicates(subset=["email"], keep="last")

        logging.info(f"Transformation terminée: {len(df)} lignes valides")

        # Sauvegarde des données transformées
        transformed_csv_path = "/tmp/users_transformed.csv"
        df.to_csv(transformed_csv_path, index=False)

        return {
            "rows_transformed": len(df),
            "temp_file": transformed_csv_path,
            "transformation_timestamp": datetime.now().isoformat(),
            "columns_final": list(df.columns),
        }

    except Exception as e:
        logging.error(f"Erreur lors de la transformation: {str(e)}")
        raise


def load_users_to_postgres(**context):
    """
    Chargement des données transformées vers PostgreSQL
    """
    try:
        # Récupération des informations de transformation
        ti = context["ti"]
        transform_info = ti.xcom_pull(task_ids="transform_users")
        temp_file = transform_info["temp_file"]

        logging.info(f"Début du chargement depuis {temp_file}")

        # Lecture des données transformées
        df = pd.read_csv(temp_file)

        # Connexion à PostgreSQL
        postgres_hook = PostgresHook(postgres_conn_id="postgres_default")

        # Insertion des données
        logging.info("Insertion des données dans PostgreSQL...")

        # Préparation des données pour l'insertion
        insert_data = []
        for _, row in df.iterrows():
            insert_data.append(
                (
                    row.get("name", ""),
                    row.get("age", None),
                    row.get("gender", ""),
                    row.get("email", ""),
                    row.get("phone", ""),
                    row.get("predicted_level", ""),
                    row.get("created_at", datetime.now()),
                    row.get("updated_at", datetime.now()),
                )
            )

        # Requête d'insertion avec gestion des conflits
        insert_query = """
        INSERT INTO users_person (name, age, gender, email, phone, predicted_level, created_at, updated_at)
        VALUES %s
        ON CONFLICT (email) 
        DO UPDATE SET 
            name = EXCLUDED.name,
            age = EXCLUDED.age,
            gender = EXCLUDED.gender,
            phone = EXCLUDED.phone,
            predicted_level = EXCLUDED.predicted_level,
            updated_at = EXCLUDED.updated_at;
        """

        # Exécution de l'insertion
        postgres_hook.insert_rows(
            table="users_person",
            rows=insert_data,
            target_fields=[
                "name",
                "age",
                "gender",
                "email",
                "phone",
                "predicted_level",
                "created_at",
                "updated_at",
            ],
            replace=False,
        )

        logging.info(f"Données chargées avec succès: {len(insert_data)} lignes")

        # Nettoyage des fichiers temporaires
        if os.path.exists(temp_file):
            os.remove(temp_file)

        extract_info = ti.xcom_pull(task_ids="extract_users")
        if os.path.exists(extract_info["temp_file"]):
            os.remove(extract_info["temp_file"])

        return {
            "rows_loaded": len(insert_data),
            "load_timestamp": datetime.now().isoformat(),
            "status": "success",
        }

    except Exception as e:
        logging.error(f"Erreur lors du chargement: {str(e)}")
        raise


def validate_etl_results(**context):
    """
    Validation des résultats de l'ETL
    """
    try:
        # Récupération des métadonnées de toutes les étapes
        ti = context["ti"]
        extract_info = ti.xcom_pull(task_ids="extract_users")
        transform_info = ti.xcom_pull(task_ids="transform_users")
        load_info = ti.xcom_pull(task_ids="load_users")

        # Validation de cohérence
        logging.info("Validation des résultats ETL...")

        # Vérification de la cohérence des données
        postgres_hook = PostgresHook(postgres_conn_id="postgres_default")

        # Comptage des utilisateurs en base
        count_query = "SELECT COUNT(*) FROM users_person WHERE source = 'excel_etl'"
        result = postgres_hook.get_first(count_query)
        users_count = result[0] if result else 0

        # Génération du rapport
        report = {
            "extraction": {
                "rows_extracted": extract_info["rows_extracted"],
                "timestamp": extract_info["extraction_timestamp"],
            },
            "transformation": {
                "rows_transformed": transform_info["rows_transformed"],
                "timestamp": transform_info["transformation_timestamp"],
            },
            "loading": {
                "rows_loaded": load_info["rows_loaded"],
                "timestamp": load_info["load_timestamp"],
            },
            "validation": {
                "users_in_db": users_count,
                "validation_timestamp": datetime.now().isoformat(),
                "data_quality_score": round(
                    (
                        transform_info["rows_transformed"]
                        / extract_info["rows_extracted"]
                    )
                    * 100,
                    2,
                ),
            },
        }

        logging.info(f"Rapport ETL: {report}")

        # Alertes si nécessaire
        if report["validation"]["data_quality_score"] < 80:
            logging.warning(
                f"Qualité des données faible: {report['validation']['data_quality_score']}%"
            )

        return report

    except Exception as e:
        logging.error(f"Erreur lors de la validation: {str(e)}")
        raise


# Définition des tâches
extract_task = PythonOperator(
    task_id="extract_users",
    python_callable=extract_users_from_excel,
    dag=dag,
    doc_md="Extraction des données utilisateurs depuis le fichier Excel",
)

transform_task = PythonOperator(
    task_id="transform_users",
    python_callable=transform_users_data,
    dag=dag,
    doc_md="Transformation et nettoyage des données utilisateurs",
)

load_task = PythonOperator(
    task_id="load_users",
    python_callable=load_users_to_postgres,
    dag=dag,
    doc_md="Chargement des données vers PostgreSQL",
)

validate_task = PythonOperator(
    task_id="validate_etl",
    python_callable=validate_etl_results,
    dag=dag,
    doc_md="Validation des résultats de l'ETL",
)

# Tâche de notification (optionnelle)
notify_task = BashOperator(
    task_id="notify_completion",
    bash_command="""
    echo "ETL Users Daily terminé avec succès à $(date)"
    echo "Consultez les logs pour plus de détails"
    """,
    dag=dag,
)

# Définition des dépendances
extract_task >> transform_task >> load_task >> validate_task >> notify_task
