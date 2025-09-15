#!/usr/bin/env python3
"""
Script de gestion de l'orchestration simple
Permet de démarrer, arrêter et gérer les tâches
"""

import argparse
import sys
import os
import json
from datetime import datetime

# Ajouter le chemin du scheduler
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler.main_scheduler import scheduler


def start_scheduler():
    """Démarre le scheduler"""
    print("🚀 Démarrage du scheduler d'orchestration...")
    scheduler.start()


def show_status():
    """Affiche le statut des tâches"""
    print("📊 Statut des tâches d'orchestration:")
    print("=" * 50)

    status = scheduler.get_status()
    for task_name, task_info in status.items():
        status_emoji = {
            "registered": "📝",
            "running": "🔄",
            "completed": "✅",
            "failed": "❌",
        }.get(task_info["status"], "❓")

        last_run = (
            task_info["last_run"].strftime("%Y-%m-%d %H:%M:%S")
            if task_info["last_run"]
            else "Jamais"
        )

        print(f"{status_emoji} {task_name}")
        print(f"   Description: {task_info['description']}")
        print(f"   Statut: {task_info['status']}")
        print(f"   Dernière exécution: {last_run}")
        print()


def run_task(task_name):
    """Exécute une tâche spécifique"""
    print(f"🎯 Exécution de la tâche: {task_name}")

    if task_name not in scheduler.tasks:
        print(f"❌ Tâche '{task_name}' non trouvée")
        print("Tâches disponibles:")
        for name in scheduler.tasks.keys():
            print(f"  - {name}")
        return False

    success = scheduler.run_task(task_name)

    if success:
        print(f"✅ Tâche '{task_name}' exécutée avec succès")
    else:
        print(f"❌ Échec de la tâche '{task_name}'")

    return success


def list_tasks():
    """Liste toutes les tâches disponibles"""
    print("📋 Tâches disponibles:")
    print("=" * 30)

    for task_name, task_info in scheduler.tasks.items():
        print(f"• {task_name}")
        print(f"  {task_info['description']}")
        print()


def show_logs():
    """Affiche les logs récents"""
    log_file = "logs/scheduler.log"

    if not os.path.exists(log_file):
        print("❌ Fichier de logs non trouvé")
        return

    print("📄 Logs récents:")
    print("=" * 30)

    try:
        with open(log_file, "r") as f:
            lines = f.readlines()
            # Afficher les 20 dernières lignes
            for line in lines[-20:]:
                print(line.strip())
    except Exception as e:
        print(f"❌ Erreur lecture logs: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Gestionnaire d'orchestration InLearning"
    )
    parser.add_argument(
        "command",
        choices=["start", "status", "run", "list", "logs"],
        help="Commande à exécuter",
    )
    parser.add_argument("--task", help="Nom de la tâche (pour la commande run)")

    args = parser.parse_args()

    if args.command == "start":
        start_scheduler()
    elif args.command == "status":
        show_status()
    elif args.command == "run":
        if not args.task:
            print("❌ Nom de tâche requis pour la commande 'run'")
            print("Utilisez --task <nom_tâche>")
            return
        run_task(args.task)
    elif args.command == "list":
        list_tasks()
    elif args.command == "logs":
        show_logs()


if __name__ == "__main__":
    main()
