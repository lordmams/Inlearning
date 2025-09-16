# 🔐 Configuration de l'Authentification Elasticsearch Cloud

## 📋 Vue d'ensemble

Pour connecter votre application à Elasticsearch Cloud, vous avez besoin des informations d'authentification. Voici comment les obtenir.

## 🔑 Méthodes d'Authentification

### 1. **API Key** (Recommandé)
✅ **Plus sécurisé**  
✅ **Permissions granulaires**  
✅ **Révocable facilement**  

### 2. **Username/Password**
⚠️ **Moins sécurisé**  
⚠️ **Permissions utilisateur complètes**  

## 🛠️ Comment Obtenir les Clés

### Étape 1: Connexion à Elastic Cloud
1. Allez sur [cloud.elastic.co](https://cloud.elastic.co)
2. Connectez-vous à votre compte
3. Sélectionnez votre déploiement

### Étape 2: Obtenir l'Endpoint
```
Votre URL actuelle:
https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443
```

### Étape 3A: Créer une API Key (Recommandé)

#### Via l'Interface Kibana:
1. **Ouvrez Kibana** depuis votre déploiement Elastic Cloud
2. **Menu → Stack Management → API Keys**
3. **Créer une nouvelle API Key**:
   - **Nom**: `elearning-app`
   - **Expiration**: 365 jours (ou selon vos besoins)
   - **Permissions**: 
     ```json
     {
       "courses": {
         "indices": [
           {
             "names": ["courses"],
             "privileges": ["create", "write", "read", "index", "delete"]
           }
         ]
       }
     }
     ```
4. **Copier l'API Key** générée (format: `base64_encoded_key`)

#### Via l'API REST:
```bash
curl -X POST "https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443/_security/api_key" \
-H "Content-Type: application/json" \
-u "elastic:your_password" \
-d '{
  "name": "elearning-app",
  "expiration": "365d",
  "role_descriptors": {
    "courses_access": {
      "indices": [
        {
          "names": ["courses"],
          "privileges": ["create", "write", "read", "index", "delete"]
        }
      ]
    }
  }
}'
```

### Étape 3B: Utiliser Username/Password

#### Utilisateur par défaut:
- **Username**: `elastic`
- **Password**: Le mot de passe que vous avez défini lors de la création du cluster

#### Créer un utilisateur dédié (Recommandé):
1. **Kibana → Stack Management → Users**
2. **Create user**:
   - **Username**: `elearning-app`
   - **Password**: `secure_password_123`
   - **Roles**: Créer un rôle personnalisé avec accès à l'index `courses`

### Étape 4: Cloud ID (Optionnel mais Recommandé)

Le **Cloud ID** simplifie la configuration:

1. **Dans Elastic Cloud Console**
2. **Votre déploiement → Copy endpoint**
3. **Cloud ID**: Format `deployment_name:base64_encoded_data`

Exemple:
```
my-elasticsearch-project:dXMtY2VudHJhbDEuZ2NwLmVsYXN0aWMtY2xvdWQuY29tOjQ0MyRhYmMxMjM0NTY3ODkwYWJjZGVmJGFiY2RlZjEyMzQ1Njc4OTA=
```

## ⚙️ Configuration dans .env

### Option 1: API Key + Cloud ID (Recommandé)
```env
# Elasticsearch Configuration
ELASTICSEARCH_ENABLED=true
ELASTICSEARCH_CLOUD_ID=my-elasticsearch-project:dXMtY2VudHJhbDEuZ2NwLmVsYXN0aWMtY2xvdWQuY29tOjQ0MyRhYmMxMjM0NTY3ODkwYWJjZGVmJGFiY2RlZjEyMzQ1Njc4OTA=
ELASTICSEARCH_INDEX=courses
ELASTICSEARCH_API_KEY=your_base64_api_key_here
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=
ELASTICSEARCH_HOST=
```

### Option 2: API Key + Host URL
```env
# Elasticsearch Configuration
ELASTICSEARCH_ENABLED=true
ELASTICSEARCH_HOST=https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443
ELASTICSEARCH_INDEX=courses
ELASTICSEARCH_API_KEY=your_base64_api_key_here
ELASTICSEARCH_USERNAME=
ELASTICSEARCH_PASSWORD=
ELASTICSEARCH_CLOUD_ID=
```

### Option 3: Username/Password + Host URL
```env
# Elasticsearch Configuration
ELASTICSEARCH_ENABLED=true
ELASTICSEARCH_HOST=https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443
ELASTICSEARCH_INDEX=courses
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your_cluster_password
ELASTICSEARCH_API_KEY=
ELASTICSEARCH_CLOUD_ID=
```

## 🧪 Test de Configuration

### 1. Modifier le script de test:
```bash
# Éditer test_elasticsearch_connection.py
nano test_elasticsearch_connection.py
```

### 2. Remplir vos credentials:
```python
# Configuration
ELASTICSEARCH_HOST = "https://your-deployment.es.region.gcp.elastic.cloud:443"
ELASTICSEARCH_INDEX = "courses"
ELASTICSEARCH_USERNAME = "elastic"  # Si pas d'API key
ELASTICSEARCH_PASSWORD = "your_password"  # Si pas d'API key
ELASTICSEARCH_API_KEY = "your_api_key"  # Recommandé
ELASTICSEARCH_CLOUD_ID = "your_cloud_id"  # Optionnel
```

### 3. Lancer le test:
```bash
python test_elasticsearch_connection.py
```

### 4. Résultat attendu:
```
🧪 Test de Connexion Elasticsearch Cloud
==================================================
🔍 Test de connexion à Elasticsearch Cloud...
📡 Host: https://your-deployment.es.region.gcp.elastic.cloud:443
🔑 Utilisation de l'authentification par API Key
☁️ Connexion via Cloud ID

1️⃣ Test de ping...
✅ Ping réussi - Connexion établie

2️⃣ Informations du cluster...
   • Nom du cluster: your-cluster-name
   • Version: 8.11.0
   • UUID: abc123...

3️⃣ Santé du cluster...
   • Statut: 🟢 green
   • Nœuds: 3
   • Indices: 0 shards actifs

4️⃣ Vérification de l'index 'courses'...
⚠️ Index 'courses' n'existe pas encore
   (Il sera créé automatiquement lors de la première indexation)

5️⃣ Test d'indexation simple...
✅ Test d'indexation réussi
   • Document ID: test-connection-auth
   • Résultat: created
   • Version: 1
🗑️ Document de test supprimé

🎉 Test de connexion terminé avec succès!
💡 Configuration Elasticsearch Cloud validée
==================================================
✅ Connexion Elasticsearch Cloud OK!
```

## 🔒 Sécurité

### Bonnes Pratiques:
1. **Utilisez des API Keys** plutôt que username/password
2. **Limitez les permissions** aux index nécessaires
3. **Définissez une expiration** pour les API Keys
4. **Révoque les clés** non utilisées
5. **Ne commitez jamais** les credentials dans Git

### Permissions Minimales pour l'API Key:
```json
{
  "courses_access": {
    "indices": [
      {
        "names": ["courses"],
        "privileges": [
          "create",    // Créer l'index
          "write",     // Indexer des documents
          "read",      // Lire les documents
          "index",     // Indexer des documents
          "delete"     // Supprimer des documents (optionnel)
        ]
      }
    ]
  }
}
```

## 🐛 Dépannage

### ❌ Erreur d'authentification:
```
security_exception: [security_exception] Reason: unable to authenticate user
```
**Solution**: Vérifiez vos credentials (API Key ou username/password)

### ❌ Erreur de permissions:
```
security_exception: action [indices:data/write/index] is unauthorized
```
**Solution**: Votre API Key/utilisateur n'a pas les permissions d'écriture sur l'index

### ❌ Erreur de connexion:
```
ConnectionError: Connection refused
```
**Solution**: Vérifiez l'URL de votre cluster Elasticsearch Cloud

### ❌ Erreur SSL:
```
SSLError: certificate verify failed
```
**Solution**: Elasticsearch Cloud utilise des certificats valides, vérifiez votre configuration réseau

## 📞 Support

- **Documentation Elastic**: [elastic.co/guide](https://www.elastic.co/guide)
- **Support Elastic Cloud**: Via votre console Elastic Cloud
- **Community**: [discuss.elastic.co](https://discuss.elastic.co)

---

**🔐 Authentification Elasticsearch Cloud configurée !** 