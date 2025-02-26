from pymongo import MongoClient
from gensim.models import Word2Vec
import json
import numpy as np

# Connexion à MongoDB
client = MongoClient("mongodb://mongo:27017/")
db = client["searchengine"]
collection = db["documents"]

# Charger le corpus de documents
with open("data/workplace-documents.json", "r", encoding="utf-8") as file:
    documents = json.load(file)

# Entraîner Word2Vec
sentences = [doc["content"].split() for doc in documents if "content" in doc]
model = Word2Vec(sentences, vector_size=100, window=5, min_count=1, workers=4)
model.save("models/word2vec.model")

# Insérer les documents vectorisés dans MongoDB
for doc in documents:
    vector = np.mean([model.wv[word] for word in doc["text"].split() if word in model.wv], axis=0)
    doc["vector"] = vector.tolist()
    collection.insert_one(doc)

print("Base de données initialisée avec succès !")