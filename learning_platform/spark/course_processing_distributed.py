"""
Module de traitement distribué des cours avec Apache Spark
Permet de traiter des milliers de cours en parallèle avec classification ML distribuée
"""

import json
import logging
import os
from pathlib import Path

from pyspark.ml import Pipeline
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.feature import *
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DistributedCourseProcessor:
    """Processeur de cours distribué utilisant Apache Spark"""

    def __init__(self, spark_master_url="spark://spark-master:7077"):
        self.spark_master_url = spark_master_url
        self.spark = None
        self._init_spark_session()

    def _init_spark_session(self):
        """Initialise la session Spark"""
        try:
            self.spark = (
                SparkSession.builder.appName("InLearning-CourseProcessing")
                .master(self.spark_master_url)
                .config("spark.sql.adaptive.enabled", "true")
                .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
                .config("spark.executor.memory", "2g")
                .config("spark.executor.cores", "2")
                .config("spark.driver.memory", "1g")
                .getOrCreate()
            )

            logger.info(
                f"✅ Session Spark initialisée avec master: {self.spark_master_url}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Erreur initialisation Spark: {e}")
            return False

    def process_courses_from_json(self, json_path, output_path=None):
        """Traite un fichier JSON de cours de manière distribuée"""
        try:
            logger.info(f"🚀 Début traitement distribué: {json_path}")

            # Schéma pour les cours
            course_schema = StructType(
                [
                    StructField("id", StringType(), True),
                    StructField("titre", StringType(), True),
                    StructField("description", StringType(), True),
                    StructField("contenus", MapType(StringType(), StringType()), True),
                    StructField("categories", ArrayType(StringType()), True),
                    StructField("niveau", StringType(), True),
                    StructField("duree", StringType(), True),
                ]
            )

            # Charger les données
            df = self.spark.read.option("multiline", "true").json(
                json_path, schema=course_schema
            )

            logger.info(f"📊 Nombre de cours chargés: {df.count()}")

            # Préparer le texte pour la classification
            df_processed = df.withColumn(
                "full_text",
                concat_ws(
                    " ",
                    coalesce(col("titre"), lit("")),
                    coalesce(col("description"), lit("")),
                    coalesce(col("contenus.texte"), lit("")),
                ),
            ).filter(col("full_text") != "")

            # Classification distribuée
            classified_df = self._classify_courses_distributed(df_processed)

            # Prédiction de niveau distribuée
            final_df = self._predict_levels_distributed(classified_df)

            # Sauvegarder les résultats
            if output_path:
                final_df.write.mode("overwrite").parquet(output_path)
                logger.info(f"💾 Résultats sauvegardés: {output_path}")

            # Retourner les statistiques
            stats = self._compute_statistics(final_df)
            return stats

        except Exception as e:
            logger.error(f"❌ Erreur traitement distribué: {e}")
            return None

    def _classify_courses_distributed(self, df):
        """Classification distribuée des cours par catégorie"""
        try:
            logger.info("🤖 Classification distribuée en cours...")

            # Tokenization
            tokenizer = Tokenizer(inputCol="full_text", outputCol="words")

            # Suppression des mots vides
            remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")

            # TF-IDF
            hashingTF = HashingTF(
                inputCol="filtered_words", outputCol="rawFeatures", numFeatures=10000
            )
            idf = IDF(inputCol="rawFeatures", outputCol="features")

            # Préparer les labels (simulation pour demo)
            categories = [
                "Python",
                "JavaScript",
                "Data Science",
                "Web Development",
                "Machine Learning",
                "Autres",
            ]
            df_with_labels = df.withColumn(
                "label_category",
                when(lower(col("full_text")).contains("python"), 0.0)
                .when(lower(col("full_text")).contains("javascript"), 1.0)
                .when(lower(col("full_text")).contains("data"), 2.0)
                .when(lower(col("full_text")).contains("web"), 3.0)
                .when(lower(col("full_text")).contains("machine"), 4.0)
                .otherwise(5.0),
            )

            # Pipeline de classification
            lr = LogisticRegression(featuresCol="features", labelCol="label_category")
            pipeline = Pipeline(stages=[tokenizer, remover, hashingTF, idf, lr])

            # Entraînement du modèle
            model = pipeline.fit(df_with_labels)

            # Prédictions
            predictions = model.transform(df_with_labels)

            # Ajouter le nom de la catégorie prédite
            category_mapping = {i: cat for i, cat in enumerate(categories)}

            def map_category(category_id):
                return category_mapping.get(int(category_id), "Autres")

            map_category_udf = udf(map_category, StringType())

            result_df = predictions.withColumn(
                "predicted_category", map_category_udf(col("prediction"))
            ).withColumn(
                "category_confidence",
                round(col("probability").getItem(col("prediction").cast("int")), 3),
            )

            logger.info("✅ Classification distribuée terminée")
            return result_df

        except Exception as e:
            logger.error(f"❌ Erreur classification: {e}")
            return df

    def _predict_levels_distributed(self, df):
        """Prédiction distribuée des niveaux de difficulté"""
        try:
            logger.info("📊 Prédiction de niveaux distribuée...")

            # Simulation de prédiction de niveau basée sur le contenu
            level_df = (
                df.withColumn(
                    "predicted_level",
                    when(
                        lower(col("full_text")).contains("débutant")
                        | lower(col("full_text")).contains("introduction")
                        | lower(col("full_text")).contains("basics"),
                        "Débutant",
                    )
                    .when(
                        lower(col("full_text")).contains("avancé")
                        | lower(col("full_text")).contains("expert")
                        | lower(col("full_text")).contains("advanced"),
                        "Avancé",
                    )
                    .otherwise("Intermédiaire"),
                )
                .withColumn(
                    "level_confidence",
                    rand() * 0.3 + 0.7,  # Simulation confidence entre 0.7 et 1.0
                )
                .withColumn("processing_timestamp", current_timestamp())
            )

            logger.info("✅ Prédiction de niveaux terminée")
            return level_df

        except Exception as e:
            logger.error(f"❌ Erreur prédiction niveaux: {e}")
            return df

    def _compute_statistics(self, df):
        """Calcule les statistiques du traitement distribué"""
        try:
            total_courses = df.count()

            # Statistiques par catégorie
            category_stats = df.groupBy("predicted_category").count().collect()

            # Statistiques par niveau
            level_stats = df.groupBy("predicted_level").count().collect()

            # Confidence moyenne
            avg_confidence = df.agg(
                avg("category_confidence").alias("avg_category_confidence"),
                avg("level_confidence").alias("avg_level_confidence"),
            ).collect()[0]

            stats = {
                "total_courses_processed": total_courses,
                "category_distribution": {
                    row["predicted_category"]: row["count"] for row in category_stats
                },
                "level_distribution": {
                    row["predicted_level"]: row["count"] for row in level_stats
                },
                "average_confidences": {
                    "category": float(avg_confidence["avg_category_confidence"]),
                    "level": float(avg_confidence["avg_level_confidence"]),
                },
            }

            logger.info(f"📈 Statistiques calculées: {stats}")
            return stats

        except Exception as e:
            logger.error(f"❌ Erreur calcul statistiques: {e}")
            return {}

    def process_streaming_courses(self, input_path="/opt/bitnami/spark/ingest/drop"):
        """Traitement en streaming des nouveaux cours"""
        try:
            logger.info(f"🌊 Démarrage streaming depuis: {input_path}")

            # Schema pour les cours en streaming
            course_schema = StructType(
                [
                    StructField("id", StringType(), True),
                    StructField("titre", StringType(), True),
                    StructField("description", StringType(), True),
                    StructField("contenus", MapType(StringType(), StringType()), True),
                ]
            )

            # Stream depuis le répertoire de dépôt
            stream_df = (
                self.spark.readStream.format("json")
                .schema(course_schema)
                .option("path", input_path)
                .load()
            )

            # Traitement en temps réel
            processed_stream = (
                stream_df.withColumn(
                    "full_text", concat_ws(" ", col("titre"), col("description"))
                )
                .withColumn("processing_time", current_timestamp())
                .withColumn("word_count", size(split(col("full_text"), " ")))
            )

            # Output vers console pour debugging
            query = (
                processed_stream.writeStream.outputMode("append")
                .format("console")
                .option("truncate", False)
                .trigger(processingTime="30 seconds")
                .start()
            )

            logger.info("✅ Streaming démarré")
            return query

        except Exception as e:
            logger.error(f"❌ Erreur streaming: {e}")
            return None

    def close(self):
        """Ferme la session Spark"""
        if self.spark:
            self.spark.stop()
            logger.info("🔒 Session Spark fermée")


def main():
    """Fonction principale pour test du processeur distribué"""
    processor = DistributedCourseProcessor()

    try:
        # Test avec un fichier exemple
        input_path = "/opt/bitnami/spark/data/course_pipeline/courses.json"
        output_path = "/opt/bitnami/spark/data/processed_courses"

        if os.path.exists(input_path):
            stats = processor.process_courses_from_json(input_path, output_path)
            print(f"📊 Résultats du traitement distribué:")
            print(json.dumps(stats, indent=2))
        else:
            logger.warning(f"⚠️ Fichier non trouvé: {input_path}")

    except Exception as e:
        logger.error(f"❌ Erreur main: {e}")
    finally:
        processor.close()


if __name__ == "__main__":
    main()
