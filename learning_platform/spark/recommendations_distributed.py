"""
Système de recommandations distribué avec Apache Spark MLlib
Utilise l'algorithme ALS (Alternating Least Squares) pour les recommandations collaboratives
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DistributedRecommendationEngine:
    """Moteur de recommandations distribué utilisant Spark MLlib"""

    def __init__(self, spark_master_url="spark://spark-master:7077"):
        self.spark_master_url = spark_master_url
        self.spark = None
        self.model = None
        self._init_spark_session()

    def _init_spark_session(self):
        """Initialise la session Spark pour les recommandations"""
        try:
            self.spark = (
                SparkSession.builder.appName("InLearning-Recommendations")
                .master(self.spark_master_url)
                .config("spark.sql.adaptive.enabled", "true")
                .config("spark.ml.als.implicitPrefs", "true")
                .getOrCreate()
            )

            logger.info("✅ Session Spark recommandations initialisée")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur init Spark recommandations: {e}")
            return False

    def create_user_course_interactions(self, courses_df, users_df):
        """Crée une matrice d'interactions utilisateur-cours simulée"""
        try:
            logger.info("🔄 Création matrice d'interactions...")

            # Simuler des interactions utilisateur-cours
            users_count = users_df.count()
            courses_count = courses_df.count()

            # Créer des interactions aléatoires mais réalistes
            interactions = (
                self.spark.range(0, users_count * 20)
                .withColumn("user_id", (col("id") % users_count).cast("int"))
                .withColumn("course_id", (col("id") % courses_count).cast("int"))
                .withColumn(
                    "rating",
                    when(rand() < 0.7, 5.0)  # 70% de notes élevées
                    .when(rand() < 0.2, 4.0)  # 20% de notes moyennes
                    .otherwise(3.0),  # 10% de notes basses
                )
                .withColumn("timestamp", current_timestamp())
                .select("user_id", "course_id", "rating", "timestamp")
            )

            # Supprimer les doublons
            interactions_clean = interactions.dropDuplicates(["user_id", "course_id"])

            logger.info(f"📊 Interactions créées: {interactions_clean.count()}")
            return interactions_clean

        except Exception as e:
            logger.error(f"❌ Erreur création interactions: {e}")
            return None

    def train_als_model(self, interactions_df):
        """Entraîne le modèle ALS distribué"""
        try:
            logger.info("🤖 Entraînement modèle ALS distribué...")

            # Division train/test
            train_df, test_df = interactions_df.randomSplit([0.8, 0.2], seed=42)

            # Configuration ALS
            als = ALS(
                maxIter=10,
                regParam=0.1,
                userCol="user_id",
                itemCol="course_id",
                ratingCol="rating",
                coldStartStrategy="drop",
                implicitPrefs=False,  # Ratings explicites
                rank=50,  # Facteurs latents
                seed=42,
            )

            # Entraînement
            self.model = als.fit(train_df)

            # Évaluation
            predictions = self.model.transform(test_df)
            evaluator = RegressionEvaluator(
                metricName="rmse", labelCol="rating", predictionCol="prediction"
            )

            rmse = evaluator.evaluate(predictions)
            logger.info(f"📈 RMSE du modèle: {rmse:.3f}")

            return {
                "model_trained": True,
                "rmse": rmse,
                "train_count": train_df.count(),
                "test_count": test_df.count(),
            }

        except Exception as e:
            logger.error(f"❌ Erreur entraînement ALS: {e}")
            return None

    def generate_user_recommendations(self, user_id, num_recommendations=10):
        """Génère des recommandations pour un utilisateur spécifique"""
        try:
            if not self.model:
                logger.error("❌ Modèle non entraîné")
                return None

            # Créer un DataFrame avec l'utilisateur
            user_df = self.spark.createDataFrame([(user_id,)], ["user_id"])

            # Générer les recommandations
            recommendations = self.model.recommendForUserSubset(
                user_df, num_recommendations
            )

            # Extraire les résultats
            results = recommendations.collect()
            if results:
                user_recs = results[0]["recommendations"]
                formatted_recs = [
                    {
                        "course_id": rec["course_id"],
                        "predicted_rating": float(rec["rating"]),
                    }
                    for rec in user_recs
                ]

                logger.info(
                    f"✅ {len(formatted_recs)} recommandations générées pour user {user_id}"
                )
                return formatted_recs

            return []

        except Exception as e:
            logger.error(f"❌ Erreur recommandations utilisateur: {e}")
            return None

    def generate_all_users_recommendations(self, num_recommendations=5):
        """Génère des recommandations pour tous les utilisateurs"""
        try:
            if not self.model:
                logger.error("❌ Modèle non entraîné")
                return None

            logger.info("🚀 Génération recommandations pour tous les utilisateurs...")

            # Recommandations pour tous les utilisateurs
            all_recommendations = self.model.recommendForAllUsers(num_recommendations)

            # Formater les résultats
            formatted_results = all_recommendations.select(
                col("user_id"), explode(col("recommendations")).alias("recommendation")
            ).select(
                col("user_id"),
                col("recommendation.course_id").alias("course_id"),
                col("recommendation.rating").alias("predicted_rating"),
            )

            results_count = formatted_results.count()
            logger.info(f"📊 {results_count} recommandations générées au total")

            return formatted_results

        except Exception as e:
            logger.error(f"❌ Erreur recommandations globales: {e}")
            return None

    def find_similar_courses(self, course_id, num_similar=5):
        """Trouve les cours similaires à un cours donné"""
        try:
            if not self.model:
                logger.error("❌ Modèle non entraîné")
                return None

            # Créer un DataFrame avec le cours
            course_df = self.spark.createDataFrame([(course_id,)], ["course_id"])

            # Recommandations d'éléments similaires
            similar_items = self.model.recommendForItemSubset(course_df, num_similar)

            # Extraire les résultats
            results = similar_items.collect()
            if results:
                similar_courses = results[0]["recommendations"]
                formatted_similar = [
                    {
                        "course_id": rec[
                            "user_id"
                        ],  # Dans item-item, user_id devient l'item similaire
                        "similarity_score": float(rec["rating"]),
                    }
                    for rec in similar_courses
                ]

                logger.info(
                    f"✅ {len(formatted_similar)} cours similaires trouvés pour course {course_id}"
                )
                return formatted_similar

            return []

        except Exception as e:
            logger.error(f"❌ Erreur cours similaires: {e}")
            return None

    def compute_recommendation_metrics(self, interactions_df):
        """Calcule les métriques de performance des recommandations"""
        try:
            logger.info("📊 Calcul métriques recommandations...")

            # Statistiques générales
            total_users = interactions_df.select("user_id").distinct().count()
            total_courses = interactions_df.select("course_id").distinct().count()
            total_interactions = interactions_df.count()

            # Distribution des ratings
            rating_distribution = interactions_df.groupBy("rating").count().collect()

            # Sparsité de la matrice
            sparsity = 1.0 - (total_interactions / (total_users * total_courses))

            # Utilisateurs actifs (plus de 5 interactions)
            active_users = (
                interactions_df.groupBy("user_id")
                .count()
                .filter(col("count") >= 5)
                .count()
            )

            metrics = {
                "total_users": total_users,
                "total_courses": total_courses,
                "total_interactions": total_interactions,
                "sparsity": round(sparsity, 4),
                "active_users": active_users,
                "rating_distribution": {
                    row["rating"]: row["count"] for row in rating_distribution
                },
            }

            logger.info(f"📈 Métriques: {json.dumps(metrics, indent=2)}")
            return metrics

        except Exception as e:
            logger.error(f"❌ Erreur calcul métriques: {e}")
            return {}

    def save_model(self, model_path):
        """Sauvegarde le modèle ALS entraîné"""
        try:
            if self.model:
                self.model.write().overwrite().save(model_path)
                logger.info(f"💾 Modèle sauvegardé: {model_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde modèle: {e}")
            return False

    def load_model(self, model_path):
        """Charge un modèle ALS pré-entraîné"""
        try:
            from pyspark.ml.recommendation import ALSModel

            self.model = ALSModel.load(model_path)
            logger.info(f"📂 Modèle chargé: {model_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur chargement modèle: {e}")
            return False

    def close(self):
        """Ferme la session Spark"""
        if self.spark:
            self.spark.stop()
            logger.info("🔒 Session Spark recommandations fermée")


def main():
    """Test du moteur de recommandations distribué"""
    engine = DistributedRecommendationEngine()

    try:
        # Simulation de données utilisateurs et cours
        users_data = [(i, f"user_{i}") for i in range(100)]
        courses_data = [(i, f"course_{i}") for i in range(50)]

        users_df = engine.spark.createDataFrame(users_data, ["user_id", "username"])
        courses_df = engine.spark.createDataFrame(courses_data, ["course_id", "title"])

        # Créer les interactions
        interactions = engine.create_user_course_interactions(courses_df, users_df)

        if interactions:
            # Calculer les métriques
            metrics = engine.compute_recommendation_metrics(interactions)

            # Entraîner le modèle
            training_results = engine.train_als_model(interactions)

            if training_results and training_results["model_trained"]:
                # Tester les recommandations
                user_recs = engine.generate_user_recommendations(
                    user_id=1, num_recommendations=5
                )
                print(f"🎯 Recommandations pour user 1: {user_recs}")

                # Sauvegarder le modèle
                model_path = "/opt/bitnami/spark/data/recommendation_model"
                engine.save_model(model_path)

    except Exception as e:
        logger.error(f"❌ Erreur test recommandations: {e}")
    finally:
        engine.close()


if __name__ == "__main__":
    main()
