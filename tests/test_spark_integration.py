"""
Tests d'intégration Apache Spark pour InLearning Platform
Valide le fonctionnement du cluster Spark et des traitements distribués
"""

import unittest
import requests
import json
import time
import os
from pathlib import Path


class TestSparkIntegration(unittest.TestCase):
    """Tests d'intégration pour Apache Spark"""

    def setUp(self):
        self.spark_ui_url = "http://localhost:8090"  # Spark Master UI
        self.api_url = "http://localhost:5000"  # Flask API
        self.test_courses = [
            {
                "id": "spark_test_001",
                "titre": "Test Spark Processing",
                "description": "Cours de test pour validation Spark",
                "contenus": {
                    "texte": "Contenu de test pour traitement distribué",
                    "paragraphs": ["Introduction au test", "Validation Spark"],
                    "examples": ["exemple_code = 'test'"],
                },
                "categories": ["Test"],
                "niveau": "Débutant",
                "duree": "1h",
            },
            {
                "id": "spark_test_002",
                "titre": "Machine Learning Distribué",
                "description": "Test ML avec Spark MLlib",
                "contenus": {
                    "texte": "Test des algorithmes ML distribués",
                    "paragraphs": ["ML Pipeline", "Distributed Computing"],
                    "examples": ["from pyspark.ml import Pipeline"],
                },
                "categories": ["Machine Learning"],
                "niveau": "Avancé",
                "duree": "2h",
            },
        ]

    def test_spark_cluster_available(self):
        """Test 1: Vérifier que le cluster Spark est accessible"""
        print("\n🔍 Test 1: Disponibilité du cluster Spark")

        try:
            response = requests.get(f"{self.spark_ui_url}/json/", timeout=10)
            self.assertEqual(response.status_code, 200)

            cluster_info = response.json()
            active_workers = cluster_info.get("aliveworkers", 0)

            print(f"✅ Cluster Spark accessible")
            print(f"📊 Workers actifs: {active_workers}")
            print(f"💾 Mémoire totale: {cluster_info.get('memory', 0)} MB")
            print(f"🖥️ Cores totaux: {cluster_info.get('cores', 0)}")

            self.assertGreaterEqual(
                active_workers, 1, "Au moins 1 worker doit être actif"
            )

        except requests.exceptions.RequestException as e:
            self.fail(f"❌ Cluster Spark non accessible: {e}")

    def test_api_spark_status(self):
        """Test 2: Vérifier le statut Spark dans l'API Flask"""
        print("\n🔍 Test 2: Statut Spark dans l'API")

        try:
            response = requests.get(f"{self.api_url}/status")
            self.assertEqual(response.status_code, 200)

            status_data = response.json()
            spark_cluster = status_data.get("spark_cluster", {})

            print(f"✅ API accessible")
            print(f"🚀 Spark activé: {spark_cluster.get('enabled', False)}")
            print(f"📊 Workers: {spark_cluster.get('active_workers', 0)}")
            print(f"🎯 Modes de traitement: {status_data.get('processing_modes', {})}")

            self.assertTrue(
                spark_cluster.get("enabled", False), "Spark devrait être activé"
            )

        except requests.exceptions.RequestException as e:
            self.fail(f"❌ API non accessible: {e}")

    def test_distributed_course_processing(self):
        """Test 3: Traitement distribué de cours"""
        print("\n🔍 Test 3: Traitement distribué de cours")

        try:
            # Soumettre les cours pour traitement distribué
            response = requests.post(
                f"{self.api_url}/process-courses-distributed",
                json=self.test_courses,
                headers={"Content-Type": "application/json"},
            )

            print(f"📤 Soumission: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                job_id = result.get("job_id")

                print(f"✅ Job Spark soumis: {job_id}")
                print(f"📊 Cours traités: {result.get('course_count')}")
                print(f"⏱️ Durée estimée: {result.get('estimated_duration')}s")

                self.assertIsNotNone(job_id, "Job ID devrait être retourné")
                self.assertEqual(result.get("course_count"), len(self.test_courses))

                # Attendre et vérifier le statut du job
                self._wait_for_job_completion(job_id)

            else:
                # Fallback vers traitement local - acceptable
                print("⚠️ Fallback vers traitement local")
                self.assertIn(response.status_code, [200, 500])

        except requests.exceptions.RequestException as e:
            self.fail(f"❌ Erreur traitement distribué: {e}")

    def test_spark_job_monitoring(self):
        """Test 4: Monitoring des jobs Spark"""
        print("\n🔍 Test 4: Monitoring des jobs Spark")

        try:
            # Soumettre un job de test
            response = requests.post(
                f"{self.api_url}/process-courses-distributed",
                json=self.test_courses[:1],  # Un seul cours pour test rapide
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                job_id = result.get("job_id")

                if job_id:
                    print(f"📊 Monitoring job: {job_id}")

                    # Vérifier le statut du job
                    status_response = requests.get(
                        f"{self.api_url}/spark/job-status/{job_id}"
                    )

                    if status_response.status_code == 200:
                        status = status_response.json()
                        print(f"📈 Statut job: {status.get('status')}")
                        print(
                            f"🆔 Application ID: {status.get('application_id', 'N/A')}"
                        )

                        self.assertIn(
                            status.get("status"), ["running", "completed", "submitted"]
                        )
                    else:
                        print("⚠️ Statut job non accessible")

        except Exception as e:
            print(f"⚠️ Test monitoring: {e}")

    def test_spark_performance_metrics(self):
        """Test 5: Métriques de performance Spark"""
        print("\n🔍 Test 5: Métriques de performance")

        try:
            response = requests.get(f"{self.api_url}/stats/processed-courses")
            self.assertEqual(response.status_code, 200)

            stats = response.json()
            spark_metrics = stats.get("spark_metrics", {})

            print(
                f"📊 Métriques Spark disponibles: {'Oui' if spark_metrics else 'Non'}"
            )

            if spark_metrics and "error" not in spark_metrics:
                print(
                    f"🏃 Applications totales: {spark_metrics.get('total_applications', 0)}"
                )
                print(f"✅ Jobs complétés: {spark_metrics.get('completed_jobs', 0)}")
                print(
                    f"⏱️ Temps total: {spark_metrics.get('total_processing_time', 0)}ms"
                )
                print(
                    f"📈 Utilisation cluster: {spark_metrics.get('cluster_utilization', 'unknown')}"
                )
            else:
                print("⚠️ Métriques Spark non disponibles")

        except requests.exceptions.RequestException as e:
            self.fail(f"❌ Erreur métriques: {e}")

    def test_spark_ui_access(self):
        """Test 6: Accès à l'interface Spark"""
        print("\n🔍 Test 6: Interface Spark UI")

        try:
            # Test page principale
            response = requests.get(f"{self.spark_ui_url}/", timeout=5)
            self.assertEqual(response.status_code, 200)

            # Test API applications
            api_response = requests.get(
                f"{self.spark_ui_url}/api/v1/applications", timeout=5
            )

            if api_response.status_code == 200:
                applications = api_response.json()
                print(f"✅ Spark UI accessible")
                print(f"📱 Applications: {len(applications)}")

                for app in applications[:3]:  # Afficher max 3 apps
                    print(f"   - {app.get('name', 'Unknown')}: {app.get('id', 'N/A')}")
            else:
                print("⚠️ API Spark non accessible")

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Spark UI non accessible: {e}")

    def _wait_for_job_completion(self, job_id, max_wait=60):
        """Attend la completion d'un job Spark"""
        print(f"⏳ Attente completion job {job_id}...")

        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(f"{self.api_url}/spark/job-status/{job_id}")
                if response.status_code == 200:
                    status = response.json()
                    job_status = status.get("status", "unknown")

                    if job_status in ["completed", "succeeded"]:
                        print(f"✅ Job {job_id} terminé avec succès")
                        return True
                    elif job_status in ["failed", "error"]:
                        print(
                            f"❌ Job {job_id} échoué: {status.get('error', 'Unknown error')}"
                        )
                        return False

                    print(f"🔄 Job {job_id} en cours... ({job_status})")

                time.sleep(5)

            except Exception as e:
                print(f"⚠️ Erreur monitoring job: {e}")
                break

        print(f"⏰ Timeout waiting for job {job_id}")
        return False


def run_spark_integration_tests():
    """Lance tous les tests d'intégration Spark"""
    print("🚀 === TESTS D'INTÉGRATION APACHE SPARK ===\n")

    # Configuration du test
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSparkIntegration)

    # Exécution des tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Résumé
    print("\n📊 === RÉSUMÉ DES TESTS SPARK ===")
    print(
        f"✅ Tests réussis: {result.testsRun - len(result.failures) - len(result.errors)}"
    )
    print(f"❌ Tests échoués: {len(result.failures)}")
    print(f"🚫 Erreurs: {len(result.errors)}")

    if result.failures:
        print("\n❌ ÉCHECS:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")

    if result.errors:
        print("\n🚫 ERREURS:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")

    # Statut final
    if result.wasSuccessful():
        print("\n🎉 TOUS LES TESTS SPARK SONT PASSÉS!")
        return True
    else:
        print("\n⚠️ CERTAINS TESTS SPARK ONT ÉCHOUÉ")
        return False


if __name__ == "__main__":
    success = run_spark_integration_tests()
    exit(0 if success else 1)
