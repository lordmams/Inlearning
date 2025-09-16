from django.urls import path

from . import api_views, views

app_name = "admin_dashboard"

urlpatterns = [
    # Vue de redirection avec vérification staff
    path("login-check/", views.admin_login_required, name="admin_login_check"),
    # Dashboard principal
    path("", views.admin_dashboard, name="dashboard"),
    path("analytics/api/", views.analytics_api, name="analytics_api"),
    path("analytics/users/", views.user_analytics, name="user_analytics"),
    path("analytics/courses/", views.course_analytics, name="course_analytics"),
    path("health/", views.system_health, name="system_health"),
    # Importation de cours
    path("courses/import/", views.course_import, name="course_import"),
    path(
        "courses/import/result/",
        views.course_import_result,
        name="course_import_result",
    ),
    path("pipeline/logs/", views.import_logs, name="import_logs"),
    path("pipeline/consumer/status/", views.consumer_status, name="consumer_status"),
    path("pipeline/consumer/start/", views.start_consumer, name="start_consumer"),
    path("pipeline/monitoring/", views.pipeline_monitoring, name="pipeline_monitoring"),
    # Elasticsearch
    path(
        "elasticsearch/status/", views.elasticsearch_status, name="elasticsearch_status"
    ),
    path("elasticsearch/reindex/", views.reindex_courses, name="reindex_courses"),
    path(
        "elasticsearch/import/", views.elasticsearch_import, name="elasticsearch_import"
    ),
    path(
        "download/template/", views.download_course_template, name="download_template"
    ),
    # API endpoints pour le consumer
    path("api/course-import/", api_views.course_import_api, name="api_course_import"),
    path("api/import-log/", api_views.import_log_api, name="api_import_log"),
    path(
        "api/consumer-status/",
        api_views.consumer_status_api,
        name="api_consumer_status",
    ),
    path(
        "api/consumer-health/",
        api_views.consumer_health_check,
        name="api_consumer_health",
    ),
    # System Monitoring URLs
    path("monitoring/", views.system_monitoring, name="system_monitoring"),
    path(
        "monitoring/check-health/",
        views.check_services_health,
        name="check_services_health",
    ),
    path(
        "monitoring/alert/<int:alert_id>/resolve/",
        views.resolve_alert,
        name="resolve_alert",
    ),
    path(
        "api/services-dashboard/",
        views.services_dashboard_api,
        name="services_dashboard_api",
    ),
    # Log retrieval URLs
    path("logs/", views.all_services_logs, name="all_services_logs"),
    path("logs/page/", views.logs_page, name="logs_page"),
    path("logs/statistics/", views.log_statistics, name="log_statistics"),
    path("logs/<str:service_name>/", views.service_logs, name="service_logs"),
    path(
        "logs/<str:service_name>/since/",
        views.service_logs_since,
        name="service_logs_since",
    ),
    # Monitoring APIs
    path("api/monitoring/update/", api_views.update_monitoring, name="api_update_monitoring"),
    path("api/system/health/", api_views.get_system_health, name="api_system_health"),
    # Export data
    path("export/", views.export_data, name="export_data"),
]
