from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from django.conf import settings
from courses.models import Course, Enrollment, QuizAttempt
from users.models import Person
from services.elasticsearch_service import elasticsearch_service
from .services import health_checker
from .log_service import log_service
import logging
import os

logger = logging.getLogger(__name__)

def admin_login_required(request):
    """Vue de redirection pour la connexion admin"""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard:dashboard')
    else:
        messages.info(request, "Veuillez vous connecter avec un compte administrateur pour accéder au dashboard.")
        return redirect('login')


@staff_member_required
def admin_dashboard(request):
    """Vue principale du dashboard administrateur"""

    # Statistiques générales
    now = timezone.now()
    last_30_days = now - timedelta(days=30)
    last_7_days = now - timedelta(days=7)

    # Utilisateurs
    total_users = User.objects.count()
    new_users_30d = User.objects.filter(date_joined__gte=last_30_days).count()
    new_users_7d = User.objects.filter(date_joined__gte=last_7_days).count()

    # Cours - récupérer depuis Elasticsearch
    total_courses = elasticsearch_service.get_course_count()
    new_courses_30d = 0  # Pas de date de création dans ES pour le moment

    # Inscriptions
    total_enrollments = Enrollment.objects.count()
    new_enrollments_30d = Enrollment.objects.filter(enrolled_at__gte=last_30_days).count()
    completed_courses = Enrollment.objects.filter(completed=True).count()
    completion_rate = (completed_courses / total_enrollments * 100) if total_enrollments > 0 else 0

    # Quiz
    total_quiz_attempts = QuizAttempt.objects.count()
    passed_attempts = QuizAttempt.objects.filter(passed=True).count()
    quiz_success_rate = (passed_attempts / total_quiz_attempts * 100) if total_quiz_attempts > 0 else 0

    # Top cours depuis Elasticsearch (simulation)
    es_courses = elasticsearch_service.search_courses(size=5)
    top_courses = []
    for hit in es_courses.get('hits', {}).get('hits', [])[:5]:
        course_data = hit['_source']
        course = {
            'title': course_data.get('cours', {}).get('titre', ''),
            'category': {'name': course_data.get('predictions', {}).get('predicted_category', 'Général')},
            'instructor': 'Instructeur IA',
            'enrollment_count': 50,  # Valeur simulée
            'difficulty': course_data.get('predictions', {}).get('predicted_level', 'Débutant'),
            'is_free': True
        }
        top_courses.append(course)

    # Top catégories depuis Elasticsearch
    top_categories = elasticsearch_service.get_categories_stats()[:5]

    # Progression par difficulté depuis Elasticsearch
    difficulty_stats = elasticsearch_service.get_levels_stats()

    # Activité récente
    recent_enrollments = Enrollment.objects.select_related('user', 'course').order_by('-enrolled_at')[:10]
    recent_users = User.objects.select_related('person_profile').order_by('-date_joined')[:10]

    context = {
        'stats': {
            'total_users': total_users,
            'new_users_30d': new_users_30d,
            'new_users_7d': new_users_7d,
            'total_courses': total_courses,
            'new_courses_30d': new_courses_30d,
            'total_enrollments': total_enrollments,
            'new_enrollments_30d': new_enrollments_30d,
            'completion_rate': round(completion_rate, 1),
            'quiz_success_rate': round(quiz_success_rate, 1),
        },
        'top_courses': top_courses,
        'top_categories': top_categories,
        'difficulty_stats': difficulty_stats,
        'recent_enrollments': recent_enrollments,
        'recent_users': recent_users,
    }

    return render(request, 'admin_dashboard/dashboard.html', context)

@staff_member_required
def analytics_api(request):
    """API pour les données d'analytics en temps réel"""
    from django.db.models import Count, Avg
    from datetime import timedelta
    from django.utils import timezone
    from services.elasticsearch_service import elasticsearch_service

    # Données pour les graphiques
    now = timezone.now()

    # Statistiques utilisateurs
    total_users = Person.objects.count()
    active_users = Person.objects.filter(
        user__last_login__gte=now - timedelta(days=30)
    ).count()
    new_users = Person.objects.filter(
        user__date_joined__gte=now - timedelta(days=30)
    ).count()

    # Calcul du taux d'engagement (utilisateurs actifs / total)
    engagement_rate = round((active_users / total_users * 100) if total_users > 0 else 0, 1)

    # Statistiques cours depuis Elasticsearch
    try:
        total_courses = elasticsearch_service.get_course_count()
        categories_stats = elasticsearch_service.get_categories_stats()
        total_categories = len(categories_stats) if categories_stats else 0

        # Calcul du nombre de cours populaires (avec plus de 10 inscriptions)
        popular_courses_count = 0  # À implémenter selon vos critères

        # Taux de complétion (simulation basée sur les données disponibles)
        completion_rate = 0  # À calculer selon vos données réelles

    except Exception as e:
        logger.error(f"Error getting course stats from Elasticsearch: {e}")
        total_courses = 0
        total_categories = 0
        popular_courses_count = 0
        completion_rate = 0

    # Inscriptions par jour (30 derniers jours)
    enrollments_by_day = []
    for i in range(30):
        date = now - timedelta(days=i)
        count = Enrollment.objects.filter(
            enrolled_at__date=date.date()
        ).count()
        enrollments_by_day.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })

    # Répartition par catégorie depuis Elasticsearch
    try:
        category_distribution = elasticsearch_service.get_categories_stats()
    except Exception as e:
        logger.error(f"Error getting category distribution: {e}")
        category_distribution = []

    # Progression moyenne par mois
    monthly_progress = []
    for i in range(12):
        month_start = now.replace(day=1) - timedelta(days=30*i)
        month_end = month_start + timedelta(days=30)

        avg_progress = Enrollment.objects.filter(
            enrolled_at__gte=month_start,
            enrolled_at__lt=month_end
        ).aggregate(avg_progress=Avg('progress'))['avg_progress'] or 0

        monthly_progress.append({
            'month': month_start.strftime('%Y-%m'),
            'progress': round(avg_progress, 1)
        })

    # Récupérer les données de health check
    try:
        system_overview = health_checker.get_system_overview()
        health_score = system_overview.get("health_percentage", 85)
        active_alerts = system_overview.get("unhealthy_services", 0)
        healthy_services = system_overview.get("healthy_services", 8)
        total_services = system_overview.get("total_services", 8)
        overall_status = system_overview.get("overall_status", "healthy")
    except Exception as e:
        logger.error(f"Error getting health check data: {e}")
        health_score = 85
        active_alerts = 0
        healthy_services = 8
        total_services = 8
        overall_status = "healthy"

    return JsonResponse({
        # Données pour les graphiques
        'enrollments_by_day': list(reversed(enrollments_by_day)),
        'category_distribution': category_distribution,
        'monthly_progress': list(reversed(monthly_progress)),

        # Statistiques utilisateurs
        'total_users': total_users,
        'active_users': active_users,
        'new_users': new_users,
        'engagement_rate': f"{engagement_rate}%",

        # Statistiques cours
        'total_courses': total_courses,
        'popular_courses': popular_courses_count,
        'total_categories': total_categories,
        'completion_rate': f"{completion_rate}%",

        # Données de health check
        "health_score": health_score,
        "active_alerts": active_alerts,
        "healthy_services": healthy_services,
        "total_services": total_services,
        "overall_status": overall_status,
    })

@staff_member_required
def user_analytics(request):
    """Analytics détaillées des utilisateurs"""
    from django.db.models import Count, Case, When, IntegerField

    try:
        # Distribution par âge
        age_distribution = Person.objects.extra(
            select={
                'age_range': '''
                    CASE 
                        WHEN age < 25 THEN '18-24'
                        WHEN age < 35 THEN '25-34'
                        WHEN age < 45 THEN '35-44'
                        ELSE '45+'
                    END
                '''
            }
        ).values('age_range').annotate(count=Count('id'))

        # Distribution par niveau d'éducation
        education_distribution = Person.objects.values('education_level').annotate(count=Count('id'))

        # Distribution par centre d'intérêt
        interest_distribution = Person.objects.values('interests').annotate(count=Count('id'))

        # Statistiques d'engagement
        total_users = Person.objects.count()
        active_users = Person.objects.filter(
            user__last_login__gte=timezone.now() - timedelta(days=30)
        ).count()

        context = {
            'age_distribution': list(age_distribution),
            'education_distribution': list(education_distribution),
            'interest_distribution': list(interest_distribution),
            'total_users': total_users,
            'active_users': active_users,
        }

        return render(request, 'admin_dashboard/user_analytics.html', context)

    except Exception as e:
        logger.error(f"Error in user analytics: {e}")
        messages.error(request, f"Erreur lors du chargement des analytics: {str(e)}")
        return redirect('admin_dashboard:dashboard')

@staff_member_required
def course_analytics(request):
    """Analytics détaillées des cours"""
    try:
        # Statistiques générales
        total_courses = elasticsearch_service.get_course_count()
        categories_stats = elasticsearch_service.get_categories_stats()
        levels_stats = elasticsearch_service.get_levels_stats()

        # Top cours par popularité (simulation)
        top_courses = []
        es_courses = elasticsearch_service.search_courses(size=10)
        for hit in es_courses.get('hits', {}).get('hits', [])[:10]:
            course_data = hit['_source']
            course = {
                'title': course_data.get('cours', {}).get('titre', ''),
                'category': course_data.get('predictions', {}).get('predicted_category', 'Général'),
                'level': course_data.get('predictions', {}).get('predicted_level', 'Débutant'),
                'enrollment_count': 50,  # Valeur simulée
            }
            top_courses.append(course)

        context = {
            'total_courses': total_courses,
            'categories_stats': categories_stats,
            'levels_stats': levels_stats,
            'top_courses': top_courses,
        }

        return render(request, 'admin_dashboard/course_analytics.html', context)

    except Exception as e:
        logger.error(f"Error in course analytics: {e}")
        messages.error(request, f"Erreur lors du chargement des analytics: {str(e)}")
        return redirect('admin_dashboard:dashboard')

@staff_member_required
def system_monitoring(request):
    """Page de monitoring système"""
    try:
        # Récupérer les services configurés et leur statut
        services_config = health_checker.services_config

        services = []

        # Enrichir les services avec leur statut actuel
        for config in services_config:
            service_name = config.get("service_type", config.get("name", "unknown"))
            try:
                # Effectuer un health check pour ce service
                result = health_checker.check_service_health(service_name)

                # Defensive: If result is a tuple, log error and mark as unhealthy
                if isinstance(result, tuple):
                    logger.error(f"Health check for {service_name} returned a tuple instead of dict: {result}")
                    service_data = {
                        'name': config.get('name', service_name),
                        'url': config.get('url', ''),
                        'status': 'unhealthy',
                        'error_message': f"Check failed: Health check returned tuple: {result}",
                        'response_time_ms': 0,
                        'uptime_percentage': 0,
                        'service_type': config.get('service_type', 'application'),
                        'is_critical': config.get('is_critical', False),
                        'time_since_last_check': 'Error',
                    }
                    services.append(service_data)
                    continue

                # Créer un objet service enrichi
                service_data = {
                    'name': config.get('name', service_name),
                    'url': config.get('url', ''),
                    'status': result.get('status', 'unknown') if isinstance(result, dict) else 'unknown',
                    'error_message': result.get('error', '') if isinstance(result, dict) else '',
                    'response_time_ms': result.get('response_time_ms', 0) if isinstance(result, dict) else 0,
                    'uptime_percentage': result.get('uptime_percentage', 0) if isinstance(result, dict) else 0,
                    'service_type': config.get('service_type', 'application'),
                    'is_critical': config.get('is_critical', False),
                    'time_since_last_check': result.get('time_since_last_check', 'Never') if isinstance(result, dict) else 'Never',
                }
                services.append(service_data)
            except Exception as service_error:
                logger.warning(f"Error checking service {service_name}: {service_error}")
                # Ajouter le service avec un statut d'erreur
                service_data = {
                    'name': config.get('name', service_name),
                    'url': config.get('url', ''),
                    'status': 'unhealthy',
                    'error_message': f"Check failed: {str(service_error)}",
                    'response_time_ms': 0,
                    'uptime_percentage': 0,
                    'service_type': config.get('service_type', 'application'),
                    'is_critical': config.get('is_critical', False),
                    'time_since_last_check': 'Error',
                }
                services.append(service_data)

        # Récupérer les dernières vérifications
        recent_checks = []
        try:
            from .models import ServiceMonitoring
            recent_checks = ServiceMonitoring.objects.order_by('-last_check')[:20]
        except Exception as model_error:
            logger.warning(f"Could not load ServiceMonitoring: {model_error}")

        # Récupérer les statistiques système
        try:
            system_overview = health_checker.get_system_overview()
        except Exception as overview_error:
            logger.warning(f"Could not get system overview: {overview_error}")
            system_overview = {
                'total_services': len(services),
                'healthy_services': 0,
                'health_score': 0,
                'active_alerts': 0
            }

        context = {
            'services': services,
            'recent_checks': recent_checks,
            'system_overview': system_overview,
        }

        return render(request, 'admin_dashboard/system_monitoring.html', context)

    except Exception as e:
        logger.error(f"Error in system monitoring: {e}")
        messages.error(request, f"Erreur monitoring: {str(e)}")
        return redirect('admin_dashboard:dashboard')

@staff_member_required
def check_services_health(request):
    """API pour vérifier la santé de tous les services"""
    try:
        # Lancer la vérification de tous les services
        results = health_checker.check_all_services()

        # Defensive: If any result is a tuple, convert to error dict
        if isinstance(results, tuple):
            logger.error(f"check_all_services returned a tuple: {results}")
            results = [{
                'status': 'unhealthy',
                'error_message': f"Check failed: check_all_services returned tuple: {results}"
            }]
        elif isinstance(results, list):
            new_results = []
            for r in results:
                if isinstance(r, tuple):
                    logger.error(f"Service health check returned a tuple: {r}")
                    new_results.append({
                        'status': 'unhealthy',
                        'error_message': f"Check failed: Service health check returned tuple: {r}"
                    })
                else:
                    new_results.append(r)
            results = new_results

        # Récupérer l'aperçu système mis à jour
        system_overview = health_checker.get_system_overview()

        return JsonResponse({
            'status': 'success',
            'services': results,
            'overview': system_overview
        })

    except Exception as e:
        logger.error(f"Error checking services health: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@staff_member_required
def service_detail(request, service_id):
    """Détail d'un service spécifique"""
    try:
        from .models import ServiceMonitoring
        service = ServiceMonitoring.objects.get(id=service_id)

        context = {
            'service': service,
        }

        return render(request, 'admin_dashboard/service_detail.html', context)

    except ServiceMonitoring.DoesNotExist:
        messages.error(request, "Service non trouvé")
        return redirect('admin_dashboard:system_monitoring')
    except Exception as e:
        logger.error(f"Error getting service detail: {e}")
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('admin_dashboard:system_monitoring')

@staff_member_required
def logs_page(request):
    """Page de consultation des logs"""
    try:
        # Récupérer les logs Django
        django_logs = log_service.get_django_logs()

        context = {
            'django_logs': django_logs,
        }

        return render(request, 'admin_dashboard/logs.html', context)

    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        messages.error(request, f"Erreur lors du chargement des logs: {str(e)}")
        return redirect('admin_dashboard:dashboard')

@staff_member_required
def get_logs(request, service_name):
    """API pour récupérer les logs d'un service"""
    try:
        lines = request.GET.get('lines', 100)
        logs_data = log_service.get_service_logs(service_name, lines=int(lines))

        return JsonResponse(logs_data)

    except Exception as e:
        logger.error(f"Error getting logs for {service_name}: {e}")
        return JsonResponse({
            'error': str(e)
        })

@staff_member_required
def get_logs_since(request, service_name):
    """API pour récupérer les logs d'un service depuis un certain temps"""
    try:
        minutes = request.GET.get('minutes', 30)
        logs_data = log_service.get_service_logs_since(service_name, minutes=int(minutes))

        return JsonResponse(logs_data)

    except Exception as e:
        logger.error(f"Error getting logs since for {service_name}: {e}")
        return JsonResponse({
            'error': str(e)
        })

@staff_member_required
def get_logs_stats(request):
    """API pour récupérer les statistiques des logs"""
    try:
        stats = log_service.get_logs_stats()

        return JsonResponse(stats)

    except Exception as e:
        logger.error(f"Error getting logs stats: {e}")
        return JsonResponse({
            'error': str(e)
        })

@staff_member_required
def service_details(request, service_id):
    """Vue détaillée d'un service"""
    try:
        from .models import ServiceMonitoring
        service = ServiceMonitoring.objects.get(id=service_id)

        # Récupérer les dernières vérifications pour ce service
        recent_checks = ServiceMonitoring.objects.filter(
            service_name=service.service_name
        ).order_by('-last_check')[:10]

        context = {
            'service': service,
            'recent_checks': recent_checks,
        }

        return render(request, 'admin_dashboard/service_details.html', context)

    except ServiceMonitoring.DoesNotExist:
        messages.error(request, "Service non trouvé")
        return redirect('admin_dashboard:system_monitoring')
    except Exception as e:
        logger.error(f"Error getting service details: {e}")
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('admin_dashboard:system_monitoring')

@staff_member_required
def resolve_alert(request, alert_id):
    """Vue pour résoudre une alerte"""
    try:
        from .models import Alert
        alert = Alert.objects.get(id=alert_id)
        alert.resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save()

        messages.success(request, "Alerte résolue avec succès")
        return redirect('admin_dashboard:system_monitoring')

    except Alert.DoesNotExist:
        messages.error(request, "Alerte non trouvée")
        return redirect('admin_dashboard:system_monitoring')
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        messages.error(request, f"Erreur: {str(e)}")
        return redirect('admin_dashboard:system_monitoring')

@staff_member_required
def services_dashboard_api(request):
    """API pour les données du dashboard des services"""
    try:
        # Récupérer les statistiques des services
        services_stats = health_checker.get_services_stats()

        # Defensive: If any service stat is a tuple, convert to error dict
        if isinstance(services_stats, tuple):
            logger.error(f"get_services_stats returned a tuple: {services_stats}")
            services_stats = [{
                'status': 'unhealthy',
                'error_message': f"Check failed: get_services_stats returned tuple: {services_stats}"
            }]
        elif isinstance(services_stats, list):
            new_stats = []
            for s in services_stats:
                if isinstance(s, tuple):
                    logger.error(f"Service stat is a tuple: {s}")
                    new_stats.append({
                        'status': 'unhealthy',
                        'error_message': f"Check failed: Service stat is tuple: {s}"
                    })
                else:
                    new_stats.append(s)
            services_stats = new_stats

        # Récupérer les alertes actives
        from .models import Alert
        active_alerts = Alert.objects.filter(resolved=False).order_by('-created_at')[:5]
        alerts_data = [{
            'id': alert.id,
            'service': alert.service_name,
            'message': alert.message,
            'level': alert.level,
            'created_at': alert.created_at.isoformat()
        } for alert in active_alerts]

        return JsonResponse({
            'services': services_stats,
            'active_alerts': alerts_data
        })

    except Exception as e:
        logger.error(f"Error getting services dashboard data: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def all_services_logs(request):
    """Vue pour afficher les logs de tous les services"""
    try:
        # Récupérer les logs de tous les services
        all_logs = log_service.get_all_services_logs()

        context = {
            'logs': all_logs,
        }

        return render(request, 'admin_dashboard/all_logs.html', context)

    except Exception as e:
        logger.error(f"Error getting all services logs: {e}")
        messages.error(request, f"Erreur lors du chargement des logs: {str(e)}")
        return redirect('admin_dashboard:dashboard')

@staff_member_required
def service_logs(request, service_name):
    """Vue pour afficher les logs d'un service spécifique"""
    try:
        # Récupérer les logs du service
        service_logs = log_service.get_service_logs(service_name)

        context = {
            'service_name': service_name,
            'logs': service_logs,
        }

        return render(request, 'admin_dashboard/service_logs.html', context)

    except Exception as e:
        logger.error(f"Error getting service logs: {e}")
        messages.error(request, f"Erreur lors du chargement des logs: {str(e)}")
        return redirect('admin_dashboard:all_services_logs')

@staff_member_required
def service_logs_since(request, service_name):
    """Vue pour afficher les logs d'un service depuis une certaine date"""
    try:
        # Récupérer le paramètre de temps (en minutes)
        minutes = request.GET.get('minutes', 30)

        # Récupérer les logs
        logs = log_service.get_service_logs_since(service_name, minutes=int(minutes))

        return JsonResponse({'logs': logs})

    except Exception as e:
        logger.error(f"Error getting service logs since: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def log_statistics(request):
    """Vue pour afficher les statistiques des logs"""
    try:
        # Récupérer les statistiques
        stats = log_service.get_logs_stats()

        return JsonResponse(stats)

    except Exception as e:
        logger.error(f"Error getting log statistics: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def system_health(request):
    """Vue pour vérifier la santé du système"""
    try:
        # Récupérer l'état du système
        system_status = health_checker.get_system_overview()
        # Defensive: If system_status is a tuple, convert to error dict
        if isinstance(system_status, tuple):
            logger.error(f"get_system_overview returned a tuple: {system_status}")
            return JsonResponse({
                'status': 'error',
                'message': f"Check failed: get_system_overview returned tuple: {system_status}"
            }, status=500)
        return JsonResponse(system_status)
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@staff_member_required
def course_import(request):
    """Page d'importation de cours"""
    return render(request, 'admin_dashboard/course_import.html')

@staff_member_required
def course_import_result(request):
    """Page de résultat d'importation de cours"""
    return render(request, 'admin_dashboard/course_import_result.html')

@staff_member_required
def import_logs(request):
    """Vue pour afficher les logs d'importation"""
    try:
        logs = log_service.get_import_logs()
        return JsonResponse({'logs': logs})
    except Exception as e:
        logger.error(f"Error getting import logs: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def consumer_status(request):
    """Vue pour vérifier le statut du consumer"""
    try:
        status = health_checker.check_consumer_status()
        # Defensive: If status is a tuple, convert to error dict
        if isinstance(status, tuple):
            logger.error(f"check_consumer_status returned a tuple: {status}")
            return JsonResponse({'error': f"Check failed: check_consumer_status returned tuple: {status}"}, status=500)
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error checking consumer status: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def start_consumer(request):
    """Vue pour démarrer le consumer"""
    try:
        result = health_checker.start_consumer()
        # Defensive: If result is a tuple, convert to error dict
        if isinstance(result, tuple):
            logger.error(f"start_consumer returned a tuple: {result}")
            return JsonResponse({'error': f"Check failed: start_consumer returned tuple: {result}"}, status=500)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error starting consumer: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def elasticsearch_status(request):
    """Vue pour vérifier le statut d'Elasticsearch"""
    try:
        status = elasticsearch_service.check_status()
        # Defensive: If status is a tuple, convert to error dict
        if isinstance(status, tuple):
            logger.error(f"elasticsearch_service.check_status returned a tuple: {status}")
            return JsonResponse({'error': f"Check failed: elasticsearch_service.check_status returned tuple: {status}"}, status=500)
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error checking Elasticsearch status: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def reindex_courses(request):
    """Vue pour réindexer les cours dans Elasticsearch"""
    try:
        result = elasticsearch_service.reindex_all()
        # Defensive: If result is a tuple, convert to error dict
        if isinstance(result, tuple):
            logger.error(f"elasticsearch_service.reindex_all returned a tuple: {result}")
            return JsonResponse({'error': f"Check failed: elasticsearch_service.reindex_all returned tuple: {result}"}, status=500)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error reindexing courses: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def elasticsearch_import(request):
    """Vue pour importer des données dans Elasticsearch"""
    try:
        result = elasticsearch_service.import_data()
        # Defensive: If result is a tuple, convert to error dict
        if isinstance(result, tuple):
            logger.error(f"elasticsearch_service.import_data returned a tuple: {result}")
            return JsonResponse({'error': f"Check failed: elasticsearch_service.import_data returned tuple: {result}"}, status=500)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error importing to Elasticsearch: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def download_course_template(request):
    """Vue pour télécharger le template de cours"""
    from django.http import FileResponse
    import os
    
    try:
        file_path = os.path.join(settings.BASE_DIR, 'static', 'templates', 'course_template.json')
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename='course_template.json')
    except Exception as e:
        logger.error(f"Error downloading template: {e}")
        messages.error(request, "Erreur lors du téléchargement du template")
        return redirect('admin_dashboard:course_import')


@staff_member_required
def pipeline_monitoring(request):
    """Vue pour le monitoring du pipeline"""
    try:
        pipeline_logs = log_service.get_pipeline_logs(lines=50)
        context = {
            "pipeline_logs": pipeline_logs,
        }
        return render(request, "admin_dashboard/pipeline_monitoring.html", context)
    except Exception as e:
        logger.error(f"Error in pipeline monitoring: {e}")
        messages.error(request, f"Erreur monitoring pipeline: {str(e)}")
        return redirect("admin_dashboard:dashboard")

@staff_member_required  
def export_data(request):
    """Vue pour l'export de données"""
    try:
        # Placeholder pour l'export de données
        return JsonResponse({"success": True, "message": "Export de données non encore implémenté"})
    except Exception as e:
        logger.error(f"Error in export data: {e}")
        return JsonResponse({"error": str(e)}, status=500)
