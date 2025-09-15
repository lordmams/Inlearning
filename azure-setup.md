# 🌐 Configuration Azure pour InLearning CI/CD

## 🏗️ Architecture Azure recommandée

### **Machines virtuelles nécessaires :**
- **Staging VM** : Standard B2s (2 vCPU, 4 GB RAM)
- **Production VM** : Standard B4ms (4 vCPU, 16 GB RAM)

## 🖥️ **1. Créer les VMs Azure**

### Via Azure CLI :
```bash
# Créer un groupe de ressources
az group create --name rg-inlearning --location "France Central"

# Créer VM Staging
az vm create \
  --resource-group rg-inlearning \
  --name vm-inlearning-staging \
  --image Ubuntu2004 \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard \
  --public-ip-address-dns-name inlearning-staging

# Créer VM Production
az vm create \
  --resource-group rg-inlearning \
  --name vm-inlearning-production \
  --image Ubuntu2004 \
  --size Standard_B4ms \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard \
  --public-ip-address-dns-name inlearning-production

# Ouvrir les ports nécessaires
az vm open-port --port 80 --resource-group rg-inlearning --name vm-inlearning-staging
az vm open-port --port 443 --resource-group rg-inlearning --name vm-inlearning-staging
az vm open-port --port 8080 --resource-group rg-inlearning --name vm-inlearning-staging

az vm open-port --port 80 --resource-group rg-inlearning --name vm-inlearning-production
az vm open-port --port 443 --resource-group rg-inlearning --name vm-inlearning-production
az vm open-port --port 8080 --resource-group rg-inlearning --name vm-inlearning-production
```

### Via Azure Portal :
1. Aller sur portal.azure.com
2. Créer une ressource → Machine virtuelle
3. Configuration staging :
   - Nom : `vm-inlearning-staging`
   - Image : Ubuntu Server 20.04 LTS
   - Taille : Standard B2s
   - Authentication : Clé SSH
4. Configuration production :
   - Nom : `vm-inlearning-production`
   - Image : Ubuntu Server 20.04 LTS
   - Taille : Standard B4ms
   - Authentication : Clé SSH

## 🔑 **2. Configuration SSH pour Azure**

### **Récupérer les adresses IP publiques :**
```bash
# Obtenir IP staging
az vm show -d -g rg-inlearning -n vm-inlearning-staging --query publicIps -o tsv

# Obtenir IP production
az vm show -d -g rg-inlearning -n vm-inlearning-production --query publicIps -o tsv
```

### **Secrets GitHub pour Azure :**
```bash
# Remplacer par vos vraies adresses IP Azure
STAGING_HOST=<IP_PUBLIQUE_STAGING>           # Ex: 20.111.22.33
STAGING_USER=azureuser
STAGING_SSH_KEY=<votre_clé_privée_SSH>

PRODUCTION_HOST=<IP_PUBLIQUE_PRODUCTION>     # Ex: 20.111.22.44
PRODUCTION_USER=azureuser
PRODUCTION_SSH_KEY=<votre_clé_privée_SSH>
```

## 🛠️ **3. Préparation des VMs Azure**

### **Se connecter à chaque VM et installer les dépendances :**

```bash
# Connexion staging
ssh azureuser@<IP_STAGING>

# Mise à jour système
sudo apt update && sudo apt upgrade -y

# Installation Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker azureuser

# Installation Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Installation Git
sudo apt install git -y

# Création utilisateur deploy
sudo useradd -m deploy
sudo usermod -aG docker deploy
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh

# Créer dossier projet
sudo mkdir -p /opt/inlearning-staging
sudo chown deploy:deploy /opt/inlearning-staging

# Installation nginx (optionnel)
sudo apt install nginx -y
```

**Répéter les mêmes commandes sur la VM de production** (en remplaçant staging par production)

## 🔐 **4. Configuration des clés SSH**

### **Générer les clés SSH sur votre machine locale :**
```bash
# Clé pour staging
ssh-keygen -t ed25519 -C "cicd-staging-azure@inlearning.com" -f ~/.ssh/azure_staging_key

# Clé pour production
ssh-keygen -t ed25519 -C "cicd-production-azure@inlearning.com" -f ~/.ssh/azure_production_key
```

### **Ajouter les clés publiques sur les VMs :**
```bash
# Copier la clé publique staging sur la VM staging
ssh-copy-id -i ~/.ssh/azure_staging_key.pub azureuser@<IP_STAGING>

# Se connecter et configurer pour l'utilisateur deploy
ssh azureuser@<IP_STAGING>
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
```

**Répéter pour la VM de production**

## 📋 **5. Secrets GitHub finaux pour Azure**

Dans GitHub → Settings → Secrets and variables → Actions :

| Secret | Valeur | Description |
|--------|---------|-------------|
| `STAGING_SSH_KEY` | Contenu de `~/.ssh/azure_staging_key` | Clé privée staging |
| `STAGING_USER` | `deploy` | Utilisateur pour déploiement |
| `STAGING_HOST` | `<IP_PUBLIQUE_STAGING>` | IP publique VM staging |
| `PRODUCTION_SSH_KEY` | Contenu de `~/.ssh/azure_production_key` | Clé privée production |
| `PRODUCTION_USER` | `deploy` | Utilisateur pour déploiement |
| `PRODUCTION_HOST` | `<IP_PUBLIQUE_PRODUCTION>` | IP publique VM production |

## 🌐 **6. Configuration DNS (optionnel)**

### **Associer un nom de domaine :**
Si vous avez un domaine (ex: inlearning.com) :

1. **Dans Azure :**
   - Créer une zone DNS
   - Ajouter les enregistrements A :
     - `staging.inlearning.com` → IP staging
     - `inlearning.com` → IP production

2. **Mettre à jour les secrets GitHub :**
   ```bash
   STAGING_HOST=staging.inlearning.com
   PRODUCTION_HOST=inlearning.com
   ```

## 💰 **7. Coûts estimés Azure**

### **VM Staging (Standard B2s) :**
- ~30-40€/mois

### **VM Production (Standard B4ms) :**
- ~120-150€/mois

### **Total estimé :** ~150-190€/mois

## 🔒 **8. Sécurité Azure**

### **Groupe de sécurité réseau :**
```bash
# Créer NSG pour limiter l'accès SSH
az network nsg create --resource-group rg-inlearning --name nsg-inlearning

# Autoriser seulement SSH, HTTP, HTTPS
az network nsg rule create \
  --resource-group rg-inlearning \
  --nsg-name nsg-inlearning \
  --name Allow-SSH \
  --protocol tcp \
  --priority 1000 \
  --destination-port-range 22 \
  --access allow

az network nsg rule create \
  --resource-group rg-inlearning \
  --nsg-name nsg-inlearning \
  --name Allow-HTTP \
  --protocol tcp \
  --priority 1100 \
  --destination-port-range 80 \
  --access allow

az network nsg rule create \
  --resource-group rg-inlearning \
  --nsg-name nsg-inlearning \
  --name Allow-HTTPS \
  --protocol tcp \
  --priority 1200 \
  --destination-port-range 443 \
  --access allow
```

## 🧪 **9. Test de connexion**

```bash
# Tester connexion staging
ssh -i ~/.ssh/azure_staging_key deploy@<IP_STAGING>

# Tester connexion production
ssh -i ~/.ssh/azure_production_key deploy@<IP_PRODUCTION>

# Vérifier Docker
docker --version
docker-compose --version
```

## ✅ **10. Checklist de déploiement**

- [ ] VMs Azure créées
- [ ] Docker installé sur les VMs
- [ ] Utilisateur `deploy` configuré
- [ ] Clés SSH configurées
- [ ] Secrets GitHub ajoutés
- [ ] Ports ouverts (80, 443, 8080)
- [ ] Test de connexion SSH OK

Une fois cette configuration terminée, votre pipeline CI/CD fonctionnera automatiquement avec vos VMs Azure ! 🚀 