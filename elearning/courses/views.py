from django.shortcuts import render

# Create your views here.
# courses/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy, reverse
from .models import Course, Category, Enrollment, Lesson, LearningPath
from .forms import CourseFilterForm
from django.http import JsonResponse
import requests
import json
import os
import logging

logger = logging.getLogger(__name__)

def convert_level_to_number(level):
    """
    Convertit le niveau textuel en nombre (1-5)
    Débutant -> 1
    Junior -> 2
    Intermédiaire -> 3
    Senior -> 4
    Expert -> 5
    """
    level_mapping = {
        'débutant': 1,
        'junior': 2,
        'intermédiaire': 3,
        'senior': 4,
        'expert': 5
    }
    return level_mapping.get(level.lower(), 1)

class DashboardView(LoginRequiredMixin, View):
    template_name = 'courses/dashboard.html'
    
    def get(self, request):
        # Obtenir les inscriptions de l'utilisateur
        enrollments = Enrollment.objects.filter(user=request.user)
        
        # Obtenir les cours en cours (non terminés)
        in_progress_courses = enrollments.filter(completed=False)
        
        # Obtenir les cours terminés
        completed_courses = enrollments.filter(completed=True)
        
        # Obtenir les cours recommandés basés sur les préférences de l'utilisateur
        recommended_courses = []
        try:
            person = request.user.person_profile
            if hasattr(person, 'preferences'):
                # Obtenir le mode d'apprentissage préféré
                preferred_mode = person.preferences.learning_mode
                # Convertir le mode d'apprentissage au format attendu par le modèle Course
                mode_mapping = {
                    'video': 'video',
                    'text': 'text',
                    'practice': 'practice'
                }
                course_mode = mode_mapping.get(preferred_mode, '')
                
                # Filtrer les cours par mode d'apprentissage
                if course_mode:
                    recommended_courses = Course.objects.filter(
                        learning_mode=course_mode
                    ).exclude(
                        enrollments__user=request.user
                    )[:4]  # Limiter à 4 cours
                
        except Exception as e:
            # Si l'utilisateur n'a pas de profil ou de préférences, ne pas recommander de cours
            pass
        
        # Si aucun cours recommandé n'a été trouvé, montrer quelques cours populaires
        if not recommended_courses:
            recommended_courses = Course.objects.all().order_by('-enrollments')[:4]
        
        # Obtenir les catégories pour la navigation
        categories = Category.objects.all()
        
        context = {
            'in_progress_courses': in_progress_courses,
            'completed_courses': completed_courses,
            'recommended_courses': recommended_courses,
            'categories': categories,
        }
        
        return render(request, self.template_name, context)

class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Course.objects.all()
        
        # Filtrer par la requête de recherche
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(instructor__icontains=search_query)
            )
        
        # Filtrer par catégorie
        category_id = self.request.GET.get('category', '')
        if category_id and category_id.isdigit():
            queryset = queryset.filter(category_id=category_id)
        
        # Filtrer par niveau de difficulté
        difficulty = self.request.GET.get('difficulty', '')
        if difficulty:
            queryset = queryset.filter(difficulty=difficulty)
        
        # Filtrer par mode d'apprentissage
        learning_mode = self.request.GET.get('learning_mode', '')
        if learning_mode:
            queryset = queryset.filter(learning_mode=learning_mode)
        
        # Filtrer par prix (gratuit ou payant)
        price_filter = self.request.GET.get('price', '')
        if price_filter == 'free':
            queryset = queryset.filter(is_free=True)
        elif price_filter == 'paid':
            queryset = queryset.filter(is_free=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ajouter le formulaire de filtre au contexte
        form = CourseFilterForm(self.request.GET)
        context['filter_form'] = form
        
        # Ajouter les paramètres de filtrage actuels pour la pagination
        context['current_filters'] = self.request.GET.copy()
        if 'page' in context['current_filters']:
            context['current_filters'].pop('page')
        
        # Ajouter toutes les catégories pour le filtre
        context['categories'] = Category.objects.all()
        
        # Ajouter les inscriptions de l'utilisateur
        user_enrollments = Enrollment.objects.filter(user=self.request.user).values_list('course_id', flat=True)
        context['user_enrollments'] = user_enrollments
        
        return context

class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Vérifier si l'utilisateur est inscrit à ce cours
        context['is_enrolled'] = Enrollment.objects.filter(
            user=self.request.user,
            course=self.object
        ).exists()
        
        # Obtenir toutes les leçons du cours
        context['lessons'] = self.object.lessons.all().order_by('order')
        
        # Si l'utilisateur est inscrit, obtenir sa progression
        if context['is_enrolled']:
            enrollment = Enrollment.objects.get(
                user=self.request.user,
                course=self.object
            )
            context['enrollment'] = enrollment
        
        # Obtenir d'autres cours de la même catégorie
        context['related_courses'] = Course.objects.filter(
            category=self.object.category
        ).exclude(id=self.object.id)[:4]
        
        return context

class EnrollCourseView(LoginRequiredMixin, View):
    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        
        # Vérifier si l'utilisateur est déjà inscrit
        if Enrollment.objects.filter(user=request.user, course=course).exists():
            messages.warning(request, "Vous êtes déjà inscrit à ce cours.")
            return redirect('course_detail', pk=pk)
        
        # Créer une nouvelle inscription
        Enrollment.objects.create(
            user=request.user,
            course=course,
            progress=0,
            completed=False
        )
        
        messages.success(request, f"Vous êtes maintenant inscrit au cours : {course.title}")
        return redirect('course_detail', pk=pk)

class UnenrollCourseView(LoginRequiredMixin, View):
    def post(self, request, pk):
        course = get_object_or_404(Course, pk=pk)
        
        # Vérifier si l'utilisateur est inscrit
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        if not enrollment:
            messages.warning(request, "Vous n'êtes pas inscrit à ce cours.")
            return redirect('course_detail', pk=pk)
        
        # Supprimer l'inscription
        enrollment.delete()
        
        messages.success(request, f"Vous vous êtes désinscrit du cours : {course.title}")
        return redirect('course_list')

class LessonDetailView(LoginRequiredMixin, DetailView):
    model = Lesson
    template_name = 'courses/lesson_detail.html'
    context_object_name = 'lesson'
    
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Vérifier si l'utilisateur est inscrit au cours
        is_enrolled = Enrollment.objects.filter(
            user=request.user,
            course=self.object.course
        ).exists()
        
        if not is_enrolled:
            messages.warning(request, "Vous devez être inscrit au cours pour accéder à cette leçon.")
            return redirect('course_detail', pk=self.object.course.pk)
        
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ajouter le cours au contexte
        context['course'] = self.object.course
        
        # Obtenir l'inscription de l'utilisateur
        enrollment = Enrollment.objects.get(
            user=self.request.user,
            course=self.object.course
        )
        context['enrollment'] = enrollment
        
        # Obtenir la leçon précédente et suivante
        all_lessons = self.object.course.lessons.all().order_by('order')
        lesson_index = list(all_lessons).index(self.object)
        
        if lesson_index > 0:
            context['previous_lesson'] = all_lessons[lesson_index - 1]
        
        if lesson_index < len(all_lessons) - 1:
            context['next_lesson'] = all_lessons[lesson_index + 1]
        
        return context

class MarkLessonCompletedView(LoginRequiredMixin, View):
    def post(self, request, lesson_pk):
        lesson = get_object_or_404(Lesson, pk=lesson_pk)
        course = lesson.course
        
        # Vérifier si l'utilisateur est inscrit au cours
        enrollment = Enrollment.objects.filter(
            user=request.user,
            course=course
        ).first()
        
        if not enrollment:
            messages.warning(request, "Vous devez être inscrit au cours pour marquer une leçon comme complétée.")
            return redirect('course_detail', pk=course.pk)
        
        # Calculer le nouveau pourcentage de progression
        total_lessons = course.lessons.count()
        increment = 100 / total_lessons if total_lessons > 0 else 0
        enrollment.progress = min(enrollment.progress + increment, 100)
        
        # Vérifier si toutes les leçons sont complétées
        if enrollment.progress >= 100:
            enrollment.completed = True
            messages.success(request, f"Félicitations ! Vous avez terminé le cours : {course.title}")
        
        enrollment.save()
        
        # Rediriger vers la prochaine leçon si disponible
        next_lesson = course.lessons.filter(order__gt=lesson.order).order_by('order').first()
        if next_lesson:
            return redirect('lesson_detail', pk=next_lesson.pk)
        else:
            return redirect('course_detail', pk=course.pk)

class GenerateLearningPathView(LoginRequiredMixin, View):
    template_name = 'courses/generate_learning_path.html'

    def get(self, request):
        # Vérifier si l'utilisateur a un profil
        if not hasattr(request.user, 'person_profile'):
            return redirect('create_profile')
        
        return render(request, self.template_name)

    def post(self, request):
        try:
            # Récupérer les données du formulaire
            subject = request.POST.get('subject')
            interests = json.loads(request.POST.get('interests', '[]'))
            
            # Vérifier que la matière est sélectionnée
            if not subject:
                return JsonResponse({
                    'success': False,
                    'error': 'Veuillez sélectionner une matière'
                })

            # Vérifier qu'au moins un centre d'intérêt est sélectionné
            if not interests:
                return JsonResponse({
                    'success': False,
                    'error': 'Veuillez sélectionner au moins un centre d\'intérêt'
                })

            # Convertir le niveau textuel en numérique
            user_level = convert_level_to_number(request.user.person_profile.predicted_level)

            # Préparer les données pour l'API
            user_data = {
                'user_id': request.user.id,
                'level': user_level,
                'subject': subject,
                'interests': interests
            }

            # Appel à l'API pour générer le parcours
            api_url = os.environ.get('FLASK_API_URL', 'http://flask_api:5000') + '/api/generate-learning-path'
            logger.info(f"Tentative de connexion à l'API: {api_url}")
            logger.info(f"Données envoyées à l'API: {user_data}")

            response = requests.post(api_url, json={'user_data': user_data})
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    learning_path_data = result.get('learning_path')
                    
                    # Sauvegarder le parcours dans la base de données
                    learning_path = LearningPath.objects.create(
                        user=request.user,
                        language=learning_path_data['language'],
                        level=learning_path_data['level'],
                        interests=learning_path_data['interests'],
                        modules=learning_path_data['modules']
                    )
                    
                    # Sauvegarder le parcours généré dans la session
                    request.session['learning_path'] = learning_path_data
                    return JsonResponse({
                        'success': True,
                        'message': 'Parcours généré et sauvegardé avec succès!',
                        'redirect_url': reverse('learning_path_detail', kwargs={'path_id': learning_path.id})
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': result.get('error', 'Erreur lors de la génération du parcours')
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Erreur de communication avec l\'API'
                })

        except Exception as e:
            logger.error(f"Erreur lors de la génération du parcours: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Une erreur est survenue lors de la génération du parcours'
            })

class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    template_name = 'courses/course_form.html'
    fields = ['title', 'description', 'category', 'difficulty', 'learning_mode', 'is_free']
    success_url = reverse_lazy('course_list')

    def form_valid(self, form):
        form.instance.instructor = self.request.user.get_full_name() or self.request.user.username
        messages.success(self.request, 'Cours créé avec succès!')
        return super().form_valid(form)

class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    template_name = 'courses/course_form.html'
    fields = ['title', 'description', 'category', 'difficulty', 'learning_mode', 'is_free']
    success_url = reverse_lazy('course_list')

    def form_valid(self, form):
        messages.success(self.request, 'Cours mis à jour avec succès!')
        return super().form_valid(form)

class CourseDeleteView(LoginRequiredMixin, DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('course_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Cours supprimé avec succès!')
        return super().delete(request, *args, **kwargs)

class LearningPathDetailView(LoginRequiredMixin, View):
    template_name = 'courses/learning_path_detail.html'

    def get(self, request, path_id):
        # Récupérer le parcours d'apprentissage depuis la base de données
        try:
            learning_path = LearningPath.objects.get(id=path_id, user=request.user)
            return render(request, self.template_name, {'learning_path': {
                'language': learning_path.language,
                'level': learning_path.level,
                'interests': learning_path.interests,
                'modules': learning_path.modules
            }})
        except LearningPath.DoesNotExist:
            messages.warning(request, "Parcours d'apprentissage non trouvé.")
            return redirect('dashboard')