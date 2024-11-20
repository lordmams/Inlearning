import yaml
from sqlalchemy import create_engine

def load_config(config_path):
    """
    Charge la configuration depuis un fichier YAML.
    """
    try:
        with open(config_path, "r") as file:
            return yaml.safe_load(file)
    except Exception as e:
        raise RuntimeError(f"Erreur lors du chargement de la configuration : {e}")

def load_data_to_postgres(df, config):
    """
    Charge les données dans une base de données PostgreSQL.
    """
    try:
        engine = create_engine(
            f"postgresql://{config['database']['user']}:{config['database']['password']}@"
            f"{config['database']['host']}:{config['database']['port']}/{config['database']['dbname']}"
        )
        df.to_sql("utilisateurs", engine, if_exists="append", index=False)
        print("Données insérées avec succès dans PostgreSQL.")
    except Exception as e:
        raise RuntimeError(f"Erreur lors du chargement des données dans PostgreSQL : {e}")
