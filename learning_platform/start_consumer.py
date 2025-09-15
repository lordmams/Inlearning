#!/usr/bin/env python3
"""
Script de démarrage du consumer de fichiers de cours pour learning_platform
"""

import os
import sys
from pathlib import Path

# Ajouter le répertoire du projet au path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.course_consumer import main

if __name__ == "__main__":
    print("🚀 Démarrage du consumer de cours (Learning Platform)...")
    print(f"📁 Répertoire de travail: {project_root}")

    # Configuration des variables d'environnement
    os.environ.setdefault("DJANGO_API_URL", "http://app:8000")

    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Arrêt du consumer demandé")
    except Exception as e:
        print(f"❌ Erreur fatale: {e}")
        sys.exit(1)
