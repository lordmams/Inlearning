#!/usr/bin/env python3
"""
Script de démarrage du consumer de fichiers de cours
"""

import os
import sys
import django
from pathlib import Path

# Ajouter le répertoire du projet au path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elearning.settings')
django.setup()

from services.consumer.consumer import main

if __name__ == "__main__":
    print("🚀 Démarrage du consumer de cours...")
    print(f"📁 Répertoire de travail: {project_root}")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️  Arrêt du consumer demandé")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        sys.exit(1) 