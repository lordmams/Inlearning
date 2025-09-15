from django.core.management.base import BaseCommand
from django.conf import settings
from services.elastic_service import ElasticService
from courses.models import Course
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Configure et initialise Elasticsearch pour les cours'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reindex',
            action='store_true',
            help='Réindexe tous les cours existants',
        )
        parser.add_argument(
            '--delete-index',
            action='store_true',
            help='Supprime l\'index existant avant de le recréer',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔍 Configuration d\'Elasticsearch...')
        )

        if not settings.ELASTICSEARCH_ENABLED:
            self.stdout.write(
                self.style.WARNING('⚠️ Elasticsearch est désactivé dans les settings')
            )
            return

        try:
            # Initialiser le service Elasticsearch
            elastic_service = ElasticService()
            
            if not elastic_service.enabled:
                self.stdout.write(
                    self.style.ERROR('❌ Impossible de se connecter à Elasticsearch')
                )
                return

            # Vérifier la santé du cluster
            health = elastic_service.health_check()
            self.stdout.write(f"📊 État du cluster: {health.get('cluster_status', 'unknown')}")

            # Supprimer l'index si demandé
            if options['delete_index']:
                self.stdout.write('🗑️ Suppression de l\'index existant...')
                try:
                    elastic_service.client.indices.delete(index=elastic_service.index_name)
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Index {elastic_service.index_name} supprimé')
                    )
                except Exception as e:
                    self.stdout.write(f'⚠️ Erreur suppression index: {e}')

            # L'index sera recréé automatiquement lors de la première indexation
            self.stdout.write('📝 Vérification/création de l\'index...')

            # Réindexer tous les cours si demandé
            if options['reindex']:
                self.stdout.write('🔄 Réindexation de tous les cours...')
                
                courses = Course.objects.all()
                total_courses = courses.count()
                
                if total_courses == 0:
                    self.stdout.write('⚠️ Aucun cours à indexer')
                else:
                    self.stdout.write(f'📚 Indexation de {total_courses} cours...')
                    
                    # Indexation en lot
                    result = elastic_service.bulk_index_courses(courses)
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Indexation terminée: {result["indexed"]} réussies, '
                            f'{result["errors"]} erreurs'
                        )
                    )

            # Afficher les statistiques
            analytics = elastic_service.get_analytics()
            if analytics:
                self.stdout.write('\n📊 Statistiques Elasticsearch:')
                self.stdout.write(f'   • Total cours indexés: {analytics.get("total_courses", 0)}')
                
                categories = analytics.get('categories', [])
                if categories:
                    self.stdout.write('   • Top 3 catégories:')
                    for cat in categories[:3]:
                        self.stdout.write(f'     - {cat["name"]}: {cat["count"]} cours')

            self.stdout.write(
                self.style.SUCCESS('\n🎉 Configuration Elasticsearch terminée!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erreur configuration Elasticsearch: {e}')
            )
            logger.error(f'Erreur setup Elasticsearch: {e}', exc_info=True) 