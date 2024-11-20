import extract
import transform
import load

def run_pipeline():
    """
    Orchestration du pipeline ETL.
    """
    try:
        print("Démarrage du pipeline ETL...")

        # Étape 1 : Chargement de la configuration
        print("Chargement de la configuration...")
        config = load.load_config("config.yml")
        print("Configuration chargée avec succès.")

        # Étape 2 : Extraction des données
        print("Extraction des données...")
        data = extract.extract_data(config["files"]["input_file"])
        print(f"Extraction terminée. Nombre de lignes extraites : {len(data)}")

        # Étape 3 : Transformation des données
        print("Transformation des données...")
        transformed_data = transform.transform_data(data)
        print("Transformation terminée.")

        # Étape 4 : Chargement des données
        print("Chargement des données dans PostgreSQL...")
        load.load_data_to_postgres(transformed_data, config["database"])
        print("Pipeline ETL terminé avec succès.")

    except Exception as e:
        print(f"Une erreur est survenue pendant l'exécution du pipeline : {e}")

if __name__ == "__main__":
    run_pipeline()
