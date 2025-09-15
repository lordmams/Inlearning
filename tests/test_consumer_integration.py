#!/usr/bin/env python3
"""
Script de test pour la nouvelle architecture Consumer intégrée
"""

import json
import os
import time
import requests
from pathlib import Path


def test_consumer_integration():
    """Test de l'intégration complète via consumer"""

    print("🧪 Test de l'architecture Consumer intégrée")
    print("=" * 50)

    # Configuration
    learning_platform_url = "http://localhost:8000"
    drop_folder = Path("learning_platform/ingest/drop")

    # 1. Vérifier que le Learning Platform API est disponible
    print("\n📡 1. Test de connexion au Learning Platform API...")
    try:
        response = requests.get(f"{learning_platform_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Learning Platform API disponible")
            print(f"   Status: {response.json()}")
        else:
            print(
                f"❌ Learning Platform API indisponible (status: {response.status_code})"
            )
            return False
    except Exception as e:
        print(f"❌ Erreur connexion Learning Platform: {e}")
        return False

    # 2. Créer un fichier de test
    print("\n📄 2. Création d'un fichier de cours de test...")
    test_course = {
        "url": "https://test.com/cours-python",
        "cours": {
            "id": "test_001",
            "titre": "Introduction à Python",
            "description": "Cours de base pour apprendre Python",
            "lien": "https://test.com/cours-python",
            "contenus": {
                "paragraphs": [
                    "Python est un langage de programmation",
                    "Il est facile à apprendre",
                ],
                "lists": [
                    ["Variables", "Fonctions", "Classes"],
                    ["Int", "String", "List"],
                ],
                "examples": ["print('Hello World')", "x = 5"],
                "texte": "Cours complet sur Python pour débutants",
                "lienVideo": "https://test.com/video-python",
            },
            "categories": ["Programmation", "Python", "Débutant"],
            "niveau": "Débutant",
            "duree": "10 heures",
            "vecteur_embedding": [],
        },
    }

    # 3. Créer le dossier drop s'il n'existe pas
    drop_folder.mkdir(parents=True, exist_ok=True)

    # 4. Déposer le fichier dans le dossier drop
    timestamp = int(time.time())
    test_filename = f"test_course_{timestamp}.json"
    test_file_path = drop_folder / test_filename

    print(f"📁 3. Dépôt du fichier dans {test_file_path}...")
    with open(test_file_path, "w", encoding="utf-8") as f:
        json.dump(test_course, f, indent=2, ensure_ascii=False)

    # Créer le fichier de métadonnées
    metadata = {
        "original_filename": test_filename,
        "format_type": "json",
        "uploaded_by": "test_script",
        "uploaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file_size": test_file_path.stat().st_size,
    }

    metadata_path = drop_folder / f"{test_filename}.meta"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Fichier déposé: {test_file_path}")
    print(f"✅ Métadonnées créées: {metadata_path}")

    # 5. Attendre le traitement par le consumer
    print("\n⏳ 4. Attente du traitement par le consumer...")
    print("   (Le consumer devrait détecter et traiter le fichier automatiquement)")

    # Vérifier que les fichiers sont traités (déplacés vers processed)
    processed_folder = Path("learning_platform/ingest/processed")
    max_wait = 30  # secondes
    start_time = time.time()

    while time.time() - start_time < max_wait:
        if not test_file_path.exists():
            print("✅ Fichier traité (déplacé du dossier drop)")

            # Vérifier s'il est dans processed
            if any(
                f.name.startswith(f"test_course_{timestamp}")
                for f in processed_folder.glob("*")
            ):
                print("✅ Fichier trouvé dans le dossier processed")
                break
            else:
                # Vérifier s'il est dans error
                error_folder = Path("learning_platform/ingest/error")
                if any(
                    f.name.startswith(f"test_course_{timestamp}")
                    for f in error_folder.glob("*")
                ):
                    print("❌ Fichier trouvé dans le dossier error")
                    break

        time.sleep(2)
        print(".", end="", flush=True)

    print()

    # 6. Tester l'API Learning Platform directement
    print("\n🔗 5. Test direct de l'API Learning Platform...")
    try:
        response = requests.post(
            f"{learning_platform_url}/process-single-course",
            json=test_course,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ API Learning Platform fonctionnelle")
            print(f"   Réponse: {result}")
        else:
            print(f"❌ Erreur API (status: {response.status_code})")
            print(f"   Réponse: {response.text}")

    except Exception as e:
        print(f"❌ Erreur test API: {e}")

    # 7. Statistiques du Learning Platform
    print("\n📊 6. Statistiques du Learning Platform...")
    try:
        response = requests.get(
            f"{learning_platform_url}/stats/processed-courses", timeout=5
        )
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Cours traités: {stats}")
        else:
            print(f"❌ Impossible d'obtenir les statistiques")
    except Exception as e:
        print(f"❌ Erreur statistiques: {e}")

    print("\n" + "=" * 50)
    print("🎯 Test de l'architecture Consumer terminé")
    print("\n💡 Architecture finale:")
    print(
        "   Django Interface → Dépôt fichier → Consumer → Learning Platform API → Elasticsearch"
    )


if __name__ == "__main__":
    test_consumer_integration()
