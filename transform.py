def transform_data(df):
    """
    Applique des transformations sur le DataFrame.
    """
    try:
        # Normalisation des emails
        df["Email"] = df["Email"].str.lower()

        # Nettoyage des numéros de téléphone (supprimer espaces et tirets)
        df["Téléphone"] = df["Téléphone"].str.replace(" ", "").str.replace("-", "")

        # Autres transformations possibles
        df["Langue préférée"] = df["Langue préférée"].fillna("Inconnu")

        return df
    except Exception as e:
        raise RuntimeError(f"Erreur lors de la transformation des données : {e}")
