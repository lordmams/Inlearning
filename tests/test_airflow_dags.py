#!/usr/bin/env python3
"""
Script de test et validation des DAGs Airflow
Teste la syntaxe, les dépendances et la structure des DAGs
"""

import importlib.util
import logging
import os
import sys
from datetime import datetime, timedelta

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_dag_import(dag_path):
    """
    Teste l'import d'un DAG
    """
    try:
        spec = importlib.util.spec_from_file_location("dag_module", dag_path)
        dag_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dag_module)

        # Vérifier qu'il y a bien un objet DAG
        dag_objects = [
            getattr(dag_module, attr)
            for attr in dir(dag_module)
            if attr == "dag"
            or (
                hasattr(getattr(dag_module, attr), "dag_id")
                if hasattr(dag_module, attr)
                else False
            )
        ]

        if dag_objects:
            logger.info(f"✅ DAG importé avec succès: {dag_path}")
            return (
                dag_objects[0] if hasattr(dag_objects[0], "dag_id") else dag_objects[0]
            )
        else:
            logger.error(f"❌ Aucun objet DAG trouvé dans: {dag_path}")
            return None

    except Exception as e:
        logger.error(f"❌ Erreur d'import du DAG {dag_path}: {str(e)}")
        return None


def validate_dag_structure(dag):
    """
    Valide la structure d'un DAG
    """
    issues = []

    # Vérifications de base
    if not dag.dag_id:
        issues.append("❌ dag_id manquant")

    if not dag.description:
        issues.append("⚠️ Description manquante")

    if not dag.schedule_interval:
        issues.append("⚠️ schedule_interval non défini")

    if not dag.default_args:
        issues.append("⚠️ default_args manquants")

    # Vérifier les tâches
    if not dag.task_dict:
        issues.append("❌ Aucune tâche définie")
    else:
        logger.info(f"📋 Tâches trouvées: {list(dag.task_dict.keys())}")

        # Vérifier les dépendances
        for task_id, task in dag.task_dict.items():
            if not task.upstream_task_ids and not task.downstream_task_ids:
                issues.append(f"⚠️ Tâche isolée: {task_id}")

    # Vérifier la configuration de retry
    if dag.default_args and "retries" not in dag.default_args:
        issues.append("⚠️ Nombre de retries non défini")

    return issues


def test_dag_scheduling(dag):
    """
    Teste la logique de scheduling d'un DAG
    """
    try:
        # Test avec une date de démarrage
        start_date = datetime(2025, 1, 1)

        if dag.schedule_interval:
            # Calculer la prochaine exécution
            # Note: Ceci est simplifié, Airflow utilise croniter pour les expressions cron
            logger.info(f"📅 Schedule: {dag.schedule_interval}")
            logger.info(f"📅 Start date: {dag.start_date}")

        return True
    except Exception as e:
        logger.error(f"❌ Erreur de scheduling: {str(e)}")
        return False


def generate_dag_graph(dag):
    """
    Génère une représentation textuelle du graphe des tâches
    """
    logger.info(f"\n🔗 Graphe du DAG: {dag.dag_id}")
    logger.info("=" * 50)

    # Trouve les tâches sans prédécesseurs (points d'entrée)
    root_tasks = [task for task in dag.task_dict.values() if not task.upstream_task_ids]

    def print_task_tree(task, indent=0):
        prefix = "  " * indent + "└─ " if indent > 0 else ""
        logger.info(f"{prefix}{task.task_id}")

        for downstream_task_id in task.downstream_task_ids:
            downstream_task = dag.task_dict[downstream_task_id]
            print_task_tree(downstream_task, indent + 1)

    for root_task in root_tasks:
        print_task_tree(root_task)

    logger.info("=" * 50)


def test_dag_tasks_configuration(dag):
    """
    Teste la configuration des tâches
    """
    issues = []

    for task_id, task in dag.task_dict.items():
        # Vérifier la documentation
        if not task.doc_md and not task.doc:
            issues.append(f"⚠️ Documentation manquante pour la tâche: {task_id}")

        # Vérifier les dépendances Python pour PythonOperator
        if hasattr(task, "python_callable"):
            try:
                # Vérifier que la fonction est callable
                if not callable(task.python_callable):
                    issues.append(f"❌ python_callable non valide pour: {task_id}")
            except:
                issues.append(
                    f"❌ Erreur lors de la validation de python_callable pour: {task_id}"
                )

    return issues


def main():
    """
    Fonction principale de test
    """
    logger.info("🚀 Début des tests des DAGs Airflow")
    logger.info("=" * 60)

    # Chemin vers les DAGs
    dags_path = "orchestration/airflow/dags"

    if not os.path.exists(dags_path):
        logger.error(f"❌ Répertoire des DAGs non trouvé: {dags_path}")
        sys.exit(1)

    # Liste des fichiers DAG
    dag_files = [
        f for f in os.listdir(dags_path) if f.endswith(".py") and not f.startswith("__")
    ]

    if not dag_files:
        logger.error(f"❌ Aucun fichier DAG trouvé dans: {dags_path}")
        sys.exit(1)

    logger.info(f"📁 DAGs trouvés: {dag_files}")

    total_issues = 0
    successful_dags = 0

    for dag_file in dag_files:
        dag_path = os.path.join(dags_path, dag_file)
        logger.info(f"\n🔍 Test du DAG: {dag_file}")
        logger.info("-" * 40)

        # Test d'import
        dag = test_dag_import(dag_path)
        if not dag:
            total_issues += 1
            continue

        # Validation de la structure
        structure_issues = validate_dag_structure(dag)
        if structure_issues:
            logger.warning("⚠️ Problèmes de structure détectés:")
            for issue in structure_issues:
                logger.warning(f"  {issue}")
            total_issues += len(structure_issues)

        # Test du scheduling
        if not test_dag_scheduling(dag):
            total_issues += 1

        # Génération du graphe
        generate_dag_graph(dag)

        # Test de la configuration des tâches
        task_issues = test_dag_tasks_configuration(dag)
        if task_issues:
            logger.warning("⚠️ Problèmes de configuration des tâches:")
            for issue in task_issues:
                logger.warning(f"  {issue}")
            total_issues += len(task_issues)

        if not structure_issues and not task_issues:
            logger.info("✅ DAG validé avec succès!")
            successful_dags += 1

        logger.info("-" * 40)

    # Résumé final
    logger.info(f"\n📊 RÉSUMÉ DES TESTS")
    logger.info("=" * 60)
    logger.info(f"DAGs testés: {len(dag_files)}")
    logger.info(f"DAGs valides: {successful_dags}")
    logger.info(f"Total des problèmes: {total_issues}")

    if total_issues == 0:
        logger.info("🎉 Tous les DAGs sont valides!")
        return 0
    else:
        logger.warning(f"⚠️ {total_issues} problème(s) détecté(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
