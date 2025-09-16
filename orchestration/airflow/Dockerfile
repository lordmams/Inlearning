FROM apache/airflow:2.7.1-python3.9

USER root

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Installation des providers et dépendances Python uniquement (pas de réinstallation d'Airflow)
RUN pip install --no-cache-dir \
    apache-airflow-providers-postgres==5.7.1 \
    pandas==2.0.3 \
    requests==2.31.0 \
    psycopg2-binary==2.9.7 