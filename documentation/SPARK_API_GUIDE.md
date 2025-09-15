# 🚀 Guide API Learning Platform

## ⚡ Démarrage rapide

### 1. Lancer l'API Learning Platform
```bash
cd learning_platform/api
python app.py
```

L'API sera disponible sur http://localhost:8000

### 2. Tester l'API
```bash
python test_spark_api.py
```

### 3. Lancer Django
```bash
docker-compose up
```

### 4. Tester l'intégration complète
1. Aller sur : http://localhost:8080/admin-dashboard/elasticsearch/import/
2. Uploader un fichier JSON ou CSV
3. Vérifier que les données sont envoyées à Spark

## 📡 Endpoints de l'API Spark

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/health` | GET | Vérification de santé |
| `/status` | GET | Statut détaillé |
| `/process-single-course` | POST | Traite 1 cours |
| `/process-courses-batch` | POST | Traite plusieurs cours |
| `/stats/processed-courses` | GET | Statistiques |

## 🧪 Test rapide avec curl

### Health Check
```bash
curl http://localhost:8000/health
```

### Test cours unique
```bash
curl -X POST http://localhost:8000/process-single-course \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test_001",
    "titre": "Python Test",
    "description": "Cours de test",
    "contenus": {
      "paragraphs": ["Test paragraph"],
      "lists": [["item1", "item2"]],
      "examples": ["print(\"hello\")"],
      "texte": "Texte de test",
      "lienVideo": ""
    },
    "categories": ["Test"],
    "niveau": "Débutant",
    "duree": "1h"
  }'
```

## 🔧 Structure des données

### Entrée (Django → Spark)
```json
{
  "id": "cours_001",
  "titre": "Titre du cours",
  "description": "Description",
  "contenus": {
    "paragraphs": ["par1", "par2"],
    "lists": [["item1", "item2"]],
    "examples": ["code example"],
    "texte": "texte principal",
    "lienVideo": "url"
  },
  "url": "url source",
  "lien": "lien cours",
  "categories": ["cat1", "cat2"],
  "niveau": "Débutant",
  "duree": "durée"
}
```

### Sortie (Spark → Django)
```json
{
  "id": "cours_001",
  "titre": "Titre du cours",
  // ... données originales ...
  "predicted_category": "Programmation",
  "category_confidence": 0.85,
  "predicted_level": "Intermédiaire",
  "level_confidence": 0.78,
  "vecteur_embedding": [0.1, 0.2, ...],
  "processed_at": "2024-01-15T10:30:00Z"
}
```

## 🎯 Avantages

✅ **Compatible Django** : Routes exactes attendues  
✅ **Enrichissement** : Catégories et niveaux prédits  
✅ **Embeddings** : Vecteurs pour la recherche  
✅ **Logs** : Traçabilité complète  
✅ **Validation** : Modèles Pydantic  
✅ **Documentation** : API auto-documentée sur /docs  

## 🚦 Statuts des réponses

- **200** : Succès
- **422** : Erreur de validation des données
- **500** : Erreur interne du pipeline
- **503** : Service non disponible

## 📊 Interface de test

L'API inclut une interface Swagger automatique :
- **Documentation** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## 🔍 Débogage

### Vérifier que Spark fonctionne
```bash
curl http://localhost:8000/health
```

### Voir les logs
```bash
python spark_api.py
# Les logs s'affichent en temps réel
```

### Tester depuis Django
1. Vérifier les settings : `SPARK_PIPELINE_URL=http://localhost:8000`
2. Lancer un import dans l'interface admin
3. Vérifier les logs Django et Spark

---

L'API Spark est maintenant **100% compatible** avec l'intégration Django ! 🎉 