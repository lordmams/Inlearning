import pandas as pd
import yaml

def load_config(config_path="config.yml"):
    """Charge la configuration à partir du fichier config.yml."""
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

def extract_data(file_path):
    """Extrait les données depuis le fichier Excel."""
    df = pd.read_excel(file_path)
    return df

if __name__ == "__main__":
    config = load_config()
    data = extract_data(config["file"]["path"])
    print(data.head())  # Affiche les premières lignes pour vérification
