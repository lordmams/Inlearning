from django.core.management.base import BaseCommand
from admin_dashboard.services import update_service_status


class Command(BaseCommand):
    help = 'Update service monitoring status'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔄 Mise à jour du monitoring...'))
        
        success = update_service_status()
        
        if success:
            self.stdout.write(self.style.SUCCESS('✅ Monitoring mis à jour avec succès!'))
        else:
            self.stdout.write(self.style.ERROR('❌ Erreur lors de la mise à jour du monitoring'))
