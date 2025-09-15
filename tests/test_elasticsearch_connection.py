#!/usr/bin/env python3
"""
Script de test pour vérifier la connexion à Elasticsearch Cloud
"""

import os
import sys
from pathlib import Path
import json

# Configuration
ELASTICSEARCH_HOST = (
    "https://my-elasticsearch-project-d09d1e.es.us-central1.gcp.elastic.cloud:443"
)
ELASTICSEARCH_INDEX = "inlearning-storage"
ELASTICSEARCH_API_KEY = (
    "T2FIYU5Ka0J5U1pfX01EQTN5QzY6XzJoOVZRTHp4Wk9EZ0V1T0dNV0ZGQQ=="  # Votre API Key
)


def test_elasticsearch_connection():
    """Test de connexion à Elasticsearch Cloud avec API Key"""
    print("🔍 Test de connexion à Elasticsearch Cloud...")
    print(f"📡 Host: {ELASTICSEARCH_HOST}")
    print(f"📊 Index: {ELASTICSEARCH_INDEX}")

    try:
        from elasticsearch import Elasticsearch

        # Configuration du client avec API Key uniquement
        if not ELASTICSEARCH_API_KEY:
            print("❌ API Key manquante - Configurez ELASTICSEARCH_API_KEY")
            return False

        client = Elasticsearch(
            [ELASTICSEARCH_HOST],
            api_key=ELASTICSEARCH_API_KEY,
            timeout=30,
            max_retries=3,
            retry_on_timeout=True,
        )

        print("🔑 Authentification via API Key")

        # Test 1: Ping
        print("\n1️⃣ Test de ping...")
        if client.ping():
            print("✅ Ping réussi - Connexion établie")
        else:
            print("❌ Ping échoué - Problème de connexion")
            return False

        # Test 2: Informations du cluster
        print("\n2️⃣ Informations du cluster...")
        try:
            cluster_info = client.info()
            print(f"   • Nom du cluster: {cluster_info.get('cluster_name', 'N/A')}")
            print(
                f"   • Version: {cluster_info.get('version', {}).get('number', 'N/A')}"
            )
            print(f"   • UUID: {cluster_info.get('cluster_uuid', 'N/A')}")
        except Exception as e:
            print(f"⚠️ Impossible de récupérer les infos: {e}")

        # Test 3: Santé du cluster
        print("\n3️⃣ Santé du cluster...")
        try:
            health = client.cluster.health()
            status = health.get("status", "unknown")
            status_icon = {"green": "🟢", "yellow": "🟡", "red": "🔴"}.get(status, "⚪")
            print(f"   • Statut: {status_icon} {status}")
            print(f"   • Nœuds: {health.get('number_of_nodes', 0)}")
            print(
                f"   • Indices: {health.get('active_primary_shards', 0)} shards actifs"
            )
        except Exception as e:
            print(f"⚠️ Impossible de récupérer la santé: {e}")

        # Test 4: Vérification de l'index
        print(f"\n4️⃣ Vérification de l'index '{ELASTICSEARCH_INDEX}'...")
        try:
            if client.indices.exists(index=ELASTICSEARCH_INDEX):
                print(f"✅ Index '{ELASTICSEARCH_INDEX}' existe")

                # Statistiques de l'index
                stats = client.indices.stats(index=ELASTICSEARCH_INDEX)
                total_docs = stats["_all"]["total"]["docs"]["count"]
                size_bytes = stats["_all"]["total"]["store"]["size_in_bytes"]
                size_mb = round(size_bytes / (1024 * 1024), 2)
                print(f"   • Documents indexés: {total_docs}")
                print(f"   • Taille: {size_mb} MB")

            else:
                print(f"⚠️ Index '{ELASTICSEARCH_INDEX}' n'existe pas encore")
                print(
                    "   (Il sera créé automatiquement lors de la première indexation)"
                )
        except Exception as e:
            print(f"⚠️ Erreur vérification index: {e}")

        # Test 5: Test d'indexation simple
        print("\n5️⃣ Test d'indexation simple...")
        try:
            test_doc = {
                "title": "Test de Connexion InLearning",
                "description": "Document de test pour vérifier l'indexation avec API Key",
                "category": "Test",
                "instructor": "InLearning Bot",
                "created_at": "2024-01-01T00:00:00Z",
                "test_document": True,
                "platform": "inlearning-storage",
            }

            response = client.index(
                index=ELASTICSEARCH_INDEX,
                id="test-connection-inlearning",
                body=test_doc,
            )

            if response.get("result") in ["created", "updated"]:
                print("✅ Test d'indexation réussi")
                print(f"   • Document ID: {response.get('_id')}")
                print(f"   • Résultat: {response.get('result')}")
                print(f"   • Version: {response.get('_version')}")

                # Supprimer le document de test
                delete_response = client.delete(
                    index=ELASTICSEARCH_INDEX, id="test-connection-inlearning"
                )
                print("🗑️ Document de test supprimé")

            else:
                print(f"⚠️ Indexation inattendue: {response}")

        except Exception as e:
            print(f"❌ Erreur test d'indexation: {e}")
            print("   Vérifiez les permissions de votre API Key")

        print("\n🎉 Test de connexion terminé avec succès!")
        print("💡 Configuration Elasticsearch Cloud validée avec API Key")
        return True

    except ImportError:
        print("❌ Module 'elasticsearch' non installé")
        print("   Installez avec: pip install elasticsearch")
        return False
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        print("\n🔧 Vérifications à faire:")
        print("   • L'URL Elasticsearch est-elle correcte?")
        print("   • L'API Key est-elle valide?")
        print("   • L'API Key a-t-elle les bonnes permissions?")
        print("   • Le réseau permet-il l'accès à Elastic Cloud?")
        return False


def test_with_django_settings():
    """Test avec les settings Django"""
    print("\n" + "=" * 50)
    print("🔧 Test avec les settings Django...")

    # Ajouter le path Django
    django_path = Path(__file__).parent / "elearning"
    sys.path.insert(0, str(django_path))

    try:
        # Configuration Django
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning.settings")

        import django

        django.setup()

        from services.elastic_service import ElasticService

        print("✅ Django configuré")

        # Test du service
        elastic_service = ElasticService()

        if elastic_service.enabled:
            print("✅ ElasticService activé")

            # Test de santé
            health = elastic_service.health_check()
            print(f"   • Santé: {health}")

        else:
            print("❌ ElasticService désactivé")
            print("   Vérifiez ELASTICSEARCH_ENABLED dans .env")

    except Exception as e:
        print(f"❌ Erreur Django: {e}")


if __name__ == "__main__":
    print("🧪 Test de Connexion Elasticsearch Cloud")
    print("=" * 50)

    # Test direct
    success = test_elasticsearch_connection()

    # Test avec Django si disponible
    if success:
        try:
            test_with_django_settings()
        except Exception as e:
            print(f"⚠️ Test Django échoué: {e}")

    print("\n" + "=" * 50)
    if success:
        print("✅ Connexion Elasticsearch Cloud OK!")
    else:
        print("❌ Problème de connexion Elasticsearch Cloud")
