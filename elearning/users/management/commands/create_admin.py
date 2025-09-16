import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crée un superutilisateur admin par défaut s'il n'existe pas"

    def handle(self, *args, **options):
        # Vérifier si un superutilisateur existe déjà
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.SUCCESS("Un superutilisateur existe déjà."))
            return

        # Récupérer les informations depuis les variables d'environnement ou utiliser des valeurs par défaut
        admin_username = os.environ.get("ADMIN_USERNAME", "admin")
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@elearning.com")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
        admin_first_name = os.environ.get("ADMIN_FIRST_NAME", "Admin")
        admin_last_name = os.environ.get("ADMIN_LAST_NAME", "System")

        try:
            # Créer le superutilisateur
            admin_user = User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                first_name=admin_first_name,
                last_name=admin_last_name,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Superutilisateur créé avec succès!\n"
                    f"   Username: {admin_user.username}\n"
                    f"   Email: {admin_user.email}\n"
                    f"   Password: {admin_password}\n"
                    f"   🚨 IMPORTANT: Changez ce mot de passe après la première connexion!"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erreur lors de la création du superutilisateur: {e}")
            )
