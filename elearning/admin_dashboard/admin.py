from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Avg, Q
from django.utils.safestring import mark_safe
from django.contrib.admin import SimpleListFilter
from django.http import HttpResponse
import csv
from datetime import datetime, timedelta

from users.models import (
    Person, Preferences, Interest, AcademicBackground, FieldOfStudy,
    ProfessionalBackground, Job, Goals, ShortTermGoal, LongTermGoal
)
from courses.models import (
    Category, Course, Enrollment, Lesson, LearningPath, Quiz, Question, Answer, QuizAttempt
)

# Personnalisation de l'interface admin
admin.site.site_header = "🎓 Administration E-Learning Platform"
admin.site.site_title = "Admin E-Learning"
admin.site.index_title = "Tableau de bord administrateur"

# Filtres personnalisés
class AgeRangeFilter(SimpleListFilter):
    title = 'Tranche d\'âge'
    parameter_name = 'age_range'

    def lookups(self, request, model_admin):
        return (
            ('18-25', '18-25 ans'),
            ('26-35', '26-35 ans'),
            ('36-45', '36-45 ans'),
            ('46+', '46+ ans'),
        )

    def queryset(self, request, queryset):
        if self.value() == '18-25':
            return queryset.filter(age__gte=18, age__lte=25)
        elif self.value() == '26-35':
            return queryset.filter(age__gte=26, age__lte=35)
        elif self.value() == '36-45':
            return queryset.filter(age__gte=36, age__lte=45)
        elif self.value() == '46+':
            return queryset.filter(age__gte=46)

class EnrollmentDateFilter(SimpleListFilter):
    title = 'Période d\'inscription'
    parameter_name = 'enrollment_period'

    def lookups(self, request, model_admin):
        return (
            ('today', 'Aujourd\'hui'),
            ('week', 'Cette semaine'),
            ('month', 'Ce mois'),
            ('quarter', 'Ce trimestre'),
        )

    def queryset(self, request, queryset):
        now = datetime.now()
        if self.value() == 'today':
            return queryset.filter(enrolled_at__date=now.date())
        elif self.value() == 'week':
            week_ago = now - timedelta(days=7)
            return queryset.filter(enrolled_at__gte=week_ago)
        elif self.value() == 'month':
            month_ago = now - timedelta(days=30)
            return queryset.filter(enrolled_at__gte=month_ago)
        elif self.value() == 'quarter':
            quarter_ago = now - timedelta(days=90)
            return queryset.filter(enrolled_at__gte=quarter_ago)

# Actions personnalisées
def export_to_csv(modeladmin, request, queryset):
    """Export des données sélectionnées vers CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{modeladmin.model._meta.model_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    
    # En-têtes
    field_names = [field.name for field in modeladmin.model._meta.fields]
    writer.writerow(field_names)
    
    # Données
    for obj in queryset:
        row = []
        for field in field_names:
            value = getattr(obj, field)
            if callable(value):
                value = value()
            row.append(str(value))
        writer.writerow(row)
    
    return response

export_to_csv.short_description = "📊 Exporter vers CSV"

def mark_as_completed(modeladmin, request, queryset):
    """Marquer les inscriptions comme terminées"""
    updated = queryset.update(completed=True, progress=100)
    modeladmin.message_user(request, f'{updated} inscription(s) marquée(s) comme terminée(s).')

mark_as_completed.short_description = "✅ Marquer comme terminé"

def reset_progress(modeladmin, request, queryset):
    """Remettre à zéro la progression"""
    updated = queryset.update(progress=0, completed=False)
    modeladmin.message_user(request, f'{updated} progression(s) remise(s) à zéro.')

reset_progress.short_description = "🔄 Remettre à zéro"

# ============================================
# ADMINISTRATION UTILISATEURS
# ============================================

class PersonInline(admin.StackedInline):
    model = Person
    can_delete = False
    verbose_name_plural = 'Profil utilisateur'
    fields = ('name', 'age', 'gender', 'email', 'phone', 'profile_picture', 'predicted_level')

class CustomUserAdmin(BaseUserAdmin):
    inlines = (PersonInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'get_person_info')
    list_filter = BaseUserAdmin.list_filter + ('person_profile__age',)
    
    def get_person_info(self, obj):
        try:
            person = obj.person_profile
            return format_html(
                '<span title="Âge: {}, Niveau: {}">👤 {}</span>',
                person.age or 'N/A',
                person.predicted_level or 'N/A',
                person.name
            )
        except:
            return format_html('<span style="color: orange;">⚠️ Profil incomplet</span>')
    
    get_person_info.short_description = 'Informations personnelles'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# ============================================
# ADMINISTRATION COURS
# ============================================

# Les modèles Course, Category, Enrollment, etc. sont déjà gérés dans courses/admin.py
# Pas besoin de les redéfinir ici pour éviter les conflits d'enregistrement

# ============================================
# CONFIGURATION AVANCÉE
# ============================================

@admin.register(LearningPath)
class LearningPathAdmin(admin.ModelAdmin):
    list_display = ('get_user_info', 'language', 'level', 'get_interests_display', 'created_at')
    list_filter = ('language', 'level', 'created_at')
    search_fields = ('user__username', 'language')
    readonly_fields = ('created_at', 'get_modules_display', 'get_interests_display')
    actions = [export_to_csv]
    
    def get_user_info(self, obj):
        return format_html('<strong>{}</strong>', obj.user.get_full_name() or obj.user.username)
    
    get_user_info.short_description = 'Utilisateur'
    
    def get_interests_display(self, obj):
        if obj.interests:
            interests = ', '.join(obj.interests) if isinstance(obj.interests, list) else str(obj.interests)
            return format_html('<span title="{}">{}</span>', interests, interests[:50] + '...' if len(interests) > 50 else interests)
        return "Aucun"
    
    get_interests_display.short_description = 'Centres d\'intérêt'
    
    def get_modules_display(self, obj):
        if obj.modules:
            return format_html('<pre>{}</pre>', str(obj.modules)[:500] + '...' if len(str(obj.modules)) > 500 else str(obj.modules))
        return "Aucun module"
    
    get_modules_display.short_description = 'Modules'

# ============================================
# ADMINISTRATION QUIZ
# ============================================

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 2
    fields = ('text', 'is_correct')

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0
    inlines = [AnswerInline]

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'learning_path', 'passing_score', 'get_questions_count', 'get_attempts_count', 'created_at')
    list_filter = ('passing_score', 'created_at')
    search_fields = ('title', 'description', 'learning_path__language')
    inlines = [QuestionInline]
    actions = [export_to_csv]
    
    def get_questions_count(self, obj):
        return format_html('<span style="font-weight: bold;">{} questions</span>', obj.questions.count())
    
    get_questions_count.short_description = 'Questions'
    
    def get_attempts_count(self, obj):
        total = obj.quizattempt_set.count()
        passed = obj.quizattempt_set.filter(passed=True).count()
        return format_html(
            '<div>{} tentatives<br/><small>{} réussies</small></div>',
            total, passed
        )
    
    get_attempts_count.short_description = 'Tentatives'

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('get_quiz_info', 'text_preview', 'order', 'points', 'get_answers_count')
    list_filter = ('quiz', 'points')
    search_fields = ('text', 'quiz__title')
    inlines = [AnswerInline]
    
    def get_quiz_info(self, obj):
        return format_html('<strong>{}</strong>', obj.quiz.title)
    
    get_quiz_info.short_description = 'Quiz'
    
    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    
    text_preview.short_description = 'Question'
    
    def get_answers_count(self, obj):
        correct = obj.answers.filter(is_correct=True).count()
        total = obj.answers.count()
        return format_html('{} réponses ({} correctes)', total, correct)
    
    get_answers_count.short_description = 'Réponses'

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('get_user_info', 'get_quiz_info', 'score', 'passed', 'started_at', 'completed_at', 'get_duration')
    list_filter = ('passed', 'started_at', 'quiz')
    search_fields = ('user__username', 'quiz__title')
    readonly_fields = ('started_at', 'get_duration', 'get_answers_detail')
    actions = [export_to_csv]
    
    def get_user_info(self, obj):
        return format_html('<strong>{}</strong>', obj.user.get_full_name() or obj.user.username)
    
    get_user_info.short_description = 'Utilisateur'
    
    def get_quiz_info(self, obj):
        return format_html('<strong>{}</strong>', obj.quiz.title)
    
    get_quiz_info.short_description = 'Quiz'
    
    def get_duration(self, obj):
        if obj.completed_at and obj.started_at:
            duration = obj.completed_at - obj.started_at
            return format_html('<span title="{}">{}</span>', duration, str(duration).split('.')[0])
        return "En cours..."
    
    get_duration.short_description = 'Durée'
    
    def get_answers_detail(self, obj):
        answers = obj.user_answers.all()
        correct = answers.filter(is_correct=True).count()
        total = answers.count()
        
        html = f'<h4>Détail des réponses ({correct}/{total})</h4><ul>'
        for answer in answers:
            color = 'green' if answer.is_correct else 'red'
            html += f'<li style="color: {color};">{answer.question.text[:50]}... - {"✓" if answer.is_correct else "✗"}</li>'
        html += '</ul>'
        
        return format_html(html)
    
    get_answers_detail.short_description = 'Détail des réponses'

# ============================================
# TABLEAU DE BORD PERSONNALISÉ
# ============================================

class AdminDashboardMixin:
    """Mixin pour ajouter des statistiques au tableau de bord"""
    
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
            
            # Statistiques générales
            stats = {
                'total_count': qs.count(),
                'recent_count': qs.filter(
                    **{f"{self.model._meta.get_field('created_at').name if hasattr(self.model, 'created_at') else 'id'}__gte": datetime.now() - timedelta(days=7)}
                ).count() if hasattr(self.model, 'created_at') else 0
            }
            
            response.context_data['stats'] = stats
            
        except (AttributeError, KeyError):
            pass
            
        return response 