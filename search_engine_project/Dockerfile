FROM python:3.9

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Exécuter init_db.py après l'installation des dépendances
RUN python app/init_db.py

CMD ["python", "app/app.py"]