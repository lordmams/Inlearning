import json
import logging
import os

import requests
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
# Create your views here.
# courses/views.py
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import (require_GET, require_http_methods,
                                          require_POST)
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
                                  UpdateView)
from services.elasticsearch_service import elasticsearch_service

from .forms import CourseFilterForm
from .models import (Answer, Category, Course, Enrollment, LearningPath,
                     Lesson, Question, Quiz, QuizAttempt, UserAnswer)

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
        "debutant": 1,
        "junior": 2,
        "intermediaire": 3,
        "senior": 4,
        "expert": 5,
        # Ajout des variantes avec accents
        "débutant": 1,
        "intermédiaire": 3,
    }
    return level_mapping.get(level.lower(), 1)


class DashboardView(LoginRequiredMixin, View):
    template_name = "courses/dashboard.html"

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
            if hasattr(person, "preferences"):
                # Obtenir le mode d'apprentissage préféré
                preferred_mode = person.preferences.learning_mode
                # Convertir le mode d'apprentissage au format attendu par le modèle Course
                mode_mapping = {
                    "video": "video",
                    "text": "text",
                    "practice": "practice",
                }
                course_mode = mode_mapping.get(preferred_mode, "")

                # Filtrer les cours par mode d'apprentissage
                if course_mode:
                    recommended_courses = Course.objects.filter(
                        learning_mode=course_mode
                    ).exclude(enrollments__user=request.user)[
                        :4
                    ]  # Limiter à 4 cours

        except Exception as e:
            # Si l'utilisateur n'a pas de profil ou de préférences, ne pas recommander de cours
            pass

        # Si aucun cours recommandé n'a été trouvé, montrer quelques cours populaires
        if not recommended_courses:
            recommended_courses = Course.objects.all().order_by("-enrollments")[:4]

        # Obtenir les catégories pour la navigation
        categories = Category.objects.all()

        context = {
            "in_progress_courses": in_progress_courses,
            "completed_courses": completed_courses,
            "recommended_courses": recommended_courses,
            "categories": categories,
        }

        return render(request, self.template_name, context)


class CourseListView(LoginRequiredMixin, View):
    template_name = "courses/course_list.html"

    def get(self, request):
        # Paramètres de recherche et filtrage
        search_query = request.GET.get("search", "")
        category = request.GET.get("category", "")
        difficulty = request.GET.get("difficulty", "")
        sort_by = request.GET.get("sort", "relevance")  # Nouveau: tri
        page = int(request.GET.get("page", 1))

        # Calcul de la pagination (plus d'options)
        per_page = int(request.GET.get("per_page", 12))
        if per_page not in [6, 12, 24, 48]:
            per_page = 12
        from_ = (page - 1) * per_page

        # Recherche dans Elasticsearch avec tri amélioré
        es_results = elasticsearch_service.search_courses(
            query=search_query if search_query else "*",
            size=per_page,
            from_=from_,
            category=category if category else None,
            level=difficulty if difficulty else None,
            sort_by=sort_by,
        )

        # Transformation des résultats Elasticsearch en format cours Django amélioré
        courses = []
        for hit in es_results.get("hits", {}).get("hits", []):
            course_data = hit["_source"]

            # Extraction des données avec validation
            titre = course_data.get("cours", {}).get("titre", "")
            description = course_data.get("cours", {}).get("description", "")
            level = course_data.get("predictions", {}).get(
                "predicted_level", "Débutant"
            )
            category = course_data.get("predictions", {}).get(
                "predicted_category", "Général"
            )

            # Calcul d'un score de pertinence basé sur le score ES
            relevance_score = hit.get("_score", 0)

            # Génération d'une couleur basée sur la catégorie
            category_colors = {
                "Programmation Générale": "#007bff",
                "Science des Données": "#28a745",
                "Intelligence Artificielle": "#dc3545",
                "Développement Web": "#fd7e14",
                "Base de Données": "#6f42c1",
                "Sécurité": "#e83e8c",
            }
            category_color = category_colors.get(category, "#6c757d")

            # Estimation de la difficulté (1-5)
            difficulty_level = convert_level_to_number(level)

            course = {
                "id": hit["_id"],
                "title": titre,
                "description": description,
                "level": level,
                "category_name": category,
                "category_color": category_color,
                "duration": course_data.get("cours", {}).get("duree", "Non spécifié"),
                "url": course_data.get("cours", {}).get("lien", "#"),
                "is_free": True,
                "difficulty": level,
                "difficulty_level": difficulty_level,
                "instructor": "Instructeur IA",
                "relevance_score": relevance_score,
                "content_length": len(
                    course_data.get("cours", {})
                    .get("contenus", {})
                    .get("paragraphs", [])
                ),
                "technologies": course_data.get("cours", {}).get("categories", [])[
                    :3
                ],  # Top 3 technologies
                "estimated_time": self._estimate_reading_time(course_data),
            }
            courses.append(course)

        # Calcul des informations de pagination
        total_hits = es_results.get("hits", {}).get("total", {}).get("value", 0)
        total_pages = (total_hits + per_page - 1) // per_page

        has_previous = page > 1
        has_next = page < total_pages

        # Obtenir les catégories disponibles depuis Elasticsearch
        categories_stats = elasticsearch_service.get_categories_stats()

        # Ajouter les inscriptions de l'utilisateur (garder la logique Django)
        user_enrollments = []
        if request.user.is_authenticated:
            user_enrollments = Enrollment.objects.filter(user=request.user).values_list(
                "course_id", flat=True
            )

        # Statistiques pour la vue
        stats = {
            "total_courses": total_hits,
            "results_on_page": len(courses),
            "search_time": es_results.get("took", 0),
            "avg_difficulty": (
                sum(c["difficulty_level"] for c in courses) / len(courses)
                if courses
                else 0
            ),
        }

        # Options de tri
        sort_options = [
            {
                "value": "relevance",
                "label": "Pertinence",
                "icon": "fas fa-sort-amount-down",
            },
            {"value": "title", "label": "Titre A-Z", "icon": "fas fa-sort-alpha-down"},
            {"value": "difficulty", "label": "Difficulté", "icon": "fas fa-signal"},
            {"value": "category", "label": "Catégorie", "icon": "fas fa-tags"},
        ]

        context = {
            "courses": courses,
            "search_query": search_query,
            "current_category": category,
            "current_difficulty": difficulty,
            "current_sort": sort_by,
            "current_per_page": per_page,
            "categories": [
                {
                    "id": cat["name"],
                    "name": cat["name"],
                    "count": cat["enrollment_count"],
                }
                for cat in categories_stats
            ],
            "user_enrollments": user_enrollments,
            "page_obj": {
                "number": page,
                "has_previous": has_previous,
                "has_next": has_next,
                "previous_page_number": page - 1 if has_previous else None,
                "next_page_number": page + 1 if has_next else None,
                "paginator": {"num_pages": total_pages, "count": total_hits},
            },
            "paginator": {"num_pages": total_pages, "count": total_hits},
            "current_filters": request.GET.copy(),
            "filter_form": CourseFilterForm(request.GET),
            "stats": stats,
            "sort_options": sort_options,
            "per_page_options": [6, 12, 24, 48],
        }

        return render(request, self.template_name, context)

    def _estimate_reading_time(self, course_data):
        """Estime le temps de lecture basé sur le contenu"""
        try:
            paragraphs = (
                course_data.get("cours", {}).get("contenus", {}).get("paragraphs", [])
            )
            total_words = 0
            for paragraph in paragraphs:
                if isinstance(paragraph, str):
                    total_words += len(paragraph.split())

            # Estimation: 200 mots par minute
            reading_time = max(1, total_words // 200)
            if reading_time < 60:
                return f"{reading_time} min"
            else:
                hours = reading_time // 60
                minutes = reading_time % 60
                return f"{hours}h{minutes:02d}"
        except:
            return "Variable"


class CourseDetailView(LoginRequiredMixin, View):
    template_name = "courses/course_detail.html"

    def get(self, request, pk):
        # Récupérer le cours depuis Elasticsearch
        es_result = elasticsearch_service.get_course_by_id(pk)

        if not es_result or not es_result.get("found"):
            # Si le cours n'existe pas dans ES, essayer dans Django
            try:
                django_course = get_object_or_404(Course, pk=pk)
                course = {
                    "id": str(django_course.id),
                    "title": django_course.title,
                    "description": django_course.description,
                    "level": django_course.difficulty,
                    "category_name": (
                        django_course.category.name
                        if django_course.category
                        else "Général"
                    ),
                    "duration": "Non spécifié",
                    "url": "#",
                    "instructor": django_course.instructor or "Instructeur",
                    "is_free": django_course.is_free,
                    "content": [],
                    "from_django": True,
                }
            except:
                return render(request, "404.html", status=404)
        else:
            # Transformer les données Elasticsearch
            course_data = es_result["_source"]
            course = {
                "id": es_result["_id"],
                "title": course_data.get("cours", {}).get("titre", ""),
                "description": course_data.get("cours", {}).get("description", ""),
                "level": course_data.get("predictions", {}).get(
                    "predicted_level", "Débutant"
                ),
                "category_name": course_data.get("predictions", {}).get(
                    "predicted_category", "Général"
                ),
                "duration": course_data.get("cours", {}).get("duree", "Non spécifié"),
                "url": course_data.get("cours", {}).get("lien", "#"),
                "instructor": "Instructeur IA",
                "is_free": True,
                "content": course_data.get("cours", {})
                .get("contenus", {})
                .get("paragraphs", []),
                "categories": course_data.get("cours", {}).get("categories", []),
                "from_elasticsearch": True,
            }

        # Vérifier si l'utilisateur est inscrit à ce cours
        is_enrolled = False
        if request.user.is_authenticated:
            if pk.isdigit():
                # Cours Django
                is_enrolled = Enrollment.objects.filter(
                    user=request.user, course_id=int(pk)
                ).exists()
            else:
                # Cours Elasticsearch - vérifier via source_url
                try:
                    django_course = Course.objects.get(
                        source_url=f"elasticsearch://{pk}"
                    )
                    is_enrolled = Enrollment.objects.filter(
                        user=request.user, course=django_course
                    ).exists()
                except Course.DoesNotExist:
                    is_enrolled = False

        # Obtenir les leçons du cours (uniquement pour les cours Django)
        lessons = []
        if course.get("from_django"):
            try:
                django_course = Course.objects.get(pk=pk)
                lessons = django_course.lessons.all().order_by("order")
            except Course.DoesNotExist:
                pass

        context = {
            "course": course,
            "is_enrolled": is_enrolled,
            "lessons": lessons,
        }

        return render(request, self.template_name, context)


class EnrollCourseView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            # Vérifier d'abord si c'est un cours Django (numérique) ou Elasticsearch (UUID)
            if pk.isdigit():
                course = get_object_or_404(Course, pk=int(pk))
                course_title = course.title
            else:
                # C'est un UUID d'Elasticsearch - créer un cours temporaire
                es_course = elasticsearch_service.get_course_by_id(pk)
                if not es_course:
                    messages.error(request, "Cours non trouvé.")
                    return redirect("course_list")

                # Créer ou récupérer un cours Django temporaire lié par source_url
                course, created = Course.objects.get_or_create(
                    source_url=es_course.get("url", ""),
                    defaults={
                        "title": es_course.get("titre", "Cours Elasticsearch"),
                        "description": es_course.get("description", ""),
                        "difficulty": es_course.get("niveau", "Débutant"),
                        "duration": es_course.get("duree", ""),
                        "is_active": True,
                    },
                )
                course_title = course.title

            # Vérifier si l'utilisateur est déjà inscrit
            if Enrollment.objects.filter(user=request.user, course=course).exists():
                messages.warning(request, "Vous êtes déjà inscrit à ce cours.")
                return redirect("course_detail", pk=pk)

            # Créer une nouvelle inscription
            Enrollment.objects.create(
                user=request.user, course=course, progress=0, completed=False
            )

            messages.success(
                request, f"Vous êtes maintenant inscrit au cours '{course_title}'!"
            )
            return redirect("course_detail", pk=pk)

        except Exception as e:
            messages.error(request, f"Erreur lors de l'inscription : {str(e)}")
            return redirect("course_list")


class UnenrollCourseView(LoginRequiredMixin, View):
    def post(self, request, pk):
        try:
            if pk.isdigit():
                # Cours Django
                course = get_object_or_404(Course, pk=int(pk))
            else:
                # Cours Elasticsearch - trouver le cours Django correspondant
                course = get_object_or_404(Course, source_url=f"elasticsearch://{pk}")

            # Vérifier si l'utilisateur est inscrit
            enrollment = Enrollment.objects.filter(
                user=request.user, course=course
            ).first()
            if not enrollment:
                messages.warning(request, "Vous n'êtes pas inscrit à ce cours.")
                return redirect("course_detail", pk=pk)

            # Supprimer l'inscription
            enrollment.delete()

            messages.success(
                request, f"Vous vous êtes désinscrit du cours : {course.title}"
            )
            return redirect("course_list")

        except Exception as e:
            messages.error(request, f"Erreur lors de la désinscription : {str(e)}")
            return redirect("course_list")


class LessonDetailView(LoginRequiredMixin, DetailView):
    model = Lesson
    template_name = "courses/lesson_detail.html"
    context_object_name = "lesson"

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # Vérifier si l'utilisateur est inscrit au cours
        is_enrolled = Enrollment.objects.filter(
            user=request.user, course=self.object.course
        ).exists()

        if not is_enrolled:
            messages.warning(
                request, "Vous devez être inscrit au cours pour accéder à cette leçon."
            )
            return redirect("course_detail", pk=self.object.course.pk)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Ajouter le cours au contexte
        context["course"] = self.object.course

        # Obtenir l'inscription de l'utilisateur
        enrollment = Enrollment.objects.get(
            user=self.request.user, course=self.object.course
        )
        context["enrollment"] = enrollment

        # Obtenir la leçon précédente et suivante
        all_lessons = self.object.course.lessons.all().order_by("order")
        lesson_index = list(all_lessons).index(self.object)

        if lesson_index > 0:
            context["previous_lesson"] = all_lessons[lesson_index - 1]

        if lesson_index < len(all_lessons) - 1:
            context["next_lesson"] = all_lessons[lesson_index + 1]

        return context


class MarkLessonCompletedView(LoginRequiredMixin, View):
    def post(self, request, lesson_pk):
        lesson = get_object_or_404(Lesson, pk=lesson_pk)
        course = lesson.course

        # Vérifier si l'utilisateur est inscrit au cours
        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()

        if not enrollment:
            messages.warning(
                request,
                "Vous devez être inscrit au cours pour marquer une leçon comme complétée.",
            )
            return redirect("course_detail", pk=course.pk)

        # Calculer le nouveau pourcentage de progression
        total_lessons = course.lessons.count()
        increment = 100 / total_lessons if total_lessons > 0 else 0
        enrollment.progress = min(enrollment.progress + increment, 100)

        # Vérifier si toutes les leçons sont complétées
        if enrollment.progress >= 100:
            enrollment.completed = True
            messages.success(
                request, f"Félicitations ! Vous avez terminé le cours : {course.title}"
            )

        enrollment.save()

        # Rediriger vers la prochaine leçon si disponible
        next_lesson = (
            course.lessons.filter(order__gt=lesson.order).order_by("order").first()
        )
        if next_lesson:
            return redirect("lesson_detail", pk=next_lesson.pk)
        else:
            return redirect("course_detail", pk=course.pk)


class GenerateLearningPathView(LoginRequiredMixin, View):
    template_name = "courses/generate_learning_path.html"

    def get(self, request):
        # Vérifier si l'utilisateur a un profil
        if not hasattr(request.user, "person_profile"):
            return redirect("create_profile")

        return render(request, self.template_name)

    def post(self, request):
        try:
            # Récupérer les données du formulaire
            subject = request.POST.get("subject")
            interests = json.loads(request.POST.get("interests", "[]"))
            provided_level = request.POST.get("level")

            # Vérifier que la matière est sélectionnée
            if not subject:
                return JsonResponse(
                    {"success": False, "error": "Veuillez sélectionner une matière"}
                )

            # Vérifier qu'au moins un centre d'intérêt est sélectionné
            if not interests:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Veuillez sélectionner au moins un centre d'intérêt",
                    }
                )

            # Utiliser le niveau fourni s'il est spécifié, sinon utiliser le niveau prédit de l'utilisateur
            if provided_level:
                user_level = convert_level_to_number(provided_level)
            else:
                user_level = convert_level_to_number(
                    request.user.person_profile.predicted_level
                )

            # Préparer les données pour l'API
            user_data = {
                "user_id": request.user.id,
                "level": user_level,
                "subject": subject,
                "interests": interests,
            }

            # Appel à l'API pour générer le parcours
            api_url = (
                os.environ.get("FLASK_API_URL", "http://flask_api:5000")
                + "/api/generate-learning-path"
            )
            logger.info(f"Tentative de connexion à l'API: {api_url}")
            logger.info(f"Données envoyées à l'API: {user_data}")

            response = requests.post(api_url, json={"user_data": user_data})

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    learning_path_data = result.get("learning_path")

                    # Sauvegarder le parcours dans la base de données
                    learning_path = LearningPath.objects.create(
                        user=request.user,
                        language=learning_path_data["language"],
                        level=user_level,  # Utiliser le niveau converti
                        interests=learning_path_data["interests"],
                        modules=learning_path_data["modules"],
                    )

                    # Sauvegarder le parcours généré dans la session
                    request.session["learning_path"] = learning_path_data
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Parcours généré et sauvegardé avec succès!",
                            "redirect_url": reverse(
                                "learning_path_detail",
                                kwargs={"path_id": learning_path.id},
                            ),
                        }
                    )
                else:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": result.get(
                                "error", "Erreur lors de la génération du parcours"
                            ),
                        }
                    )
            else:
                return JsonResponse(
                    {"success": False, "error": "Erreur de communication avec l'API"}
                )

        except Exception as e:
            logger.error(f"Erreur lors de la génération du parcours: {str(e)}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "Une erreur est survenue lors de la génération du parcours",
                }
            )


class CourseCreateView(LoginRequiredMixin, CreateView):
    model = Course
    template_name = "courses/course_form.html"
    fields = [
        "title",
        "description",
        "category",
        "difficulty",
        "learning_mode",
        "is_free",
    ]
    success_url = reverse_lazy("course_list")

    def form_valid(self, form):
        form.instance.instructor = (
            self.request.user.get_full_name() or self.request.user.username
        )
        messages.success(self.request, "Cours créé avec succès!")
        return super().form_valid(form)


class CourseUpdateView(LoginRequiredMixin, UpdateView):
    model = Course
    template_name = "courses/course_form.html"
    fields = [
        "title",
        "description",
        "category",
        "difficulty",
        "learning_mode",
        "is_free",
    ]
    success_url = reverse_lazy("course_list")

    def form_valid(self, form):
        messages.success(self.request, "Cours mis à jour avec succès!")
        return super().form_valid(form)


class CourseDeleteView(LoginRequiredMixin, DeleteView):
    model = Course
    template_name = "courses/course_confirm_delete.html"
    success_url = reverse_lazy("course_list")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Cours supprimé avec succès!")
        return super().delete(request, *args, **kwargs)


class LearningPathDetailView(LoginRequiredMixin, View):
    template_name = "courses/learning_path_detail.html"

    def get(self, request, path_id):
        learning_path = get_object_or_404(LearningPath, id=path_id, user=request.user)

        # Préparer les données des quiz avec les tentatives de l'utilisateur
        quizzes_with_attempts = []
        for quiz in learning_path.quizzes.all():
            attempts = quiz.quizattempt_set.filter(user=request.user).order_by(
                "-completed_at"
            )
            quizzes_with_attempts.append({"quiz": quiz, "attempts": attempts})

        return render(
            request,
            self.template_name,
            {
                "learning_path": learning_path,
                "quizzes_with_attempts": quizzes_with_attempts,
            },
        )


@require_http_methods(["GET"])
def claude_advice(request):
    try:
        parcours_id = request.GET.get("parcours_id")
        if not parcours_id:
            return JsonResponse(
                {"success": False, "error": "ID du parcours manquant"}, status=400
            )

        learning_path = LearningPath.objects.get(id=parcours_id)

        # Préparer les données pour l'API Flask
        data = {"modules": learning_path.modules}

        # Appeler l'API Flask
        api_url = os.environ.get("FLASK_API_URL", "http://flask_api:5000")
        if not api_url.startswith("http"):
            api_url = f"http://{api_url}"
        api_url = f"{api_url}/api/claude-advice"

        logger.info(f"Tentative de connexion à l'API: {api_url}")
        logger.info(f"Données envoyées à l'API: {data}")

        try:
            response = requests.post(
                api_url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=30,  # Ajout d'un timeout de 30 secondes
            )
            response.raise_for_status()  # Lève une exception pour les codes d'erreur HTTP

            api_response = response.json()
            if api_response.get("success"):
                return JsonResponse(
                    {
                        "success": True,
                        "suggestions": api_response.get("suggestions", []),
                    }
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "error": api_response.get("error", "Erreur inconnue"),
                    },
                    status=500,
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de connexion à l'API Flask: {str(e)}")
            return JsonResponse(
                {"success": False, "error": f"Erreur de connexion à l'API: {str(e)}"},
                status=503,
            )

    except LearningPath.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Parcours non trouvé"}, status=404
        )
    except Exception as e:
        logger.error(f"Erreur dans claude_advice: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def improve_learning_path(request):
    try:
        data = json.loads(request.body)
        learning_path = data.get("learning_path")

        if not learning_path:
            return JsonResponse(
                {"success": False, "error": "Parcours d'apprentissage manquant"},
                status=400,
            )

        # Appeler l'API Flask pour obtenir les améliorations
        flask_api_url = os.environ.get("FLASK_API_URL", "http://localhost:5000")
        response = requests.post(
            f"{flask_api_url}/api/improve-learning-path",
            json={"learning_path": learning_path},
        )

        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            logger.error(f"Erreur API Flask: {response.status_code} - {response.text}")
            return JsonResponse(
                {
                    "success": False,
                    "error": "Erreur lors de l'amélioration du parcours",
                },
                status=500,
            )

    except Exception as e:
        logger.error(f"Erreur dans improve_learning_path: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


class QuizView(LoginRequiredMixin, View):
    template_name = "courses/quiz.html"

    def get(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)

        # Vérifier si l'utilisateur a déjà une tentative en cours
        attempt = QuizAttempt.objects.filter(
            user=request.user, quiz=quiz, completed_at__isnull=True
        ).first()

        if not attempt:
            attempt = QuizAttempt.objects.create(user=request.user, quiz=quiz)

        questions = quiz.questions.all().order_by("order")
        return render(
            request,
            self.template_name,
            {"quiz": quiz, "questions": questions, "attempt": attempt},
        )

    def post(self, request, quiz_id):
        quiz = get_object_or_404(Quiz, id=quiz_id)
        attempt = get_object_or_404(
            QuizAttempt, user=request.user, quiz=quiz, completed_at__isnull=True
        )

        # Calculer le score
        total_points = 0
        earned_points = 0

        for question in quiz.questions.all():
            answer_id = request.POST.get(f"question_{question.id}")
            if answer_id:
                selected_answer = Answer.objects.get(id=answer_id)
                is_correct = selected_answer.is_correct

                # Enregistrer la réponse de l'utilisateur
                UserAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_answer=selected_answer,
                    is_correct=is_correct,
                )

                if is_correct:
                    earned_points += question.points

            total_points += question.points

        # Calculer le pourcentage
        score = (earned_points / total_points) * 100 if total_points > 0 else 0
        passed = score >= quiz.passing_score

        # Mettre à jour la tentative
        attempt.score = score
        attempt.passed = passed
        attempt.completed_at = timezone.now()
        attempt.save()

        return redirect("quiz_result", attempt_id=attempt.id)


class QuizResultView(LoginRequiredMixin, View):
    template_name = "courses/quiz_result.html"

    def get(self, request, attempt_id):
        attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
        user_answers = attempt.user_answers.all().select_related(
            "question", "selected_answer"
        )

        return render(
            request,
            self.template_name,
            {"attempt": attempt, "user_answers": user_answers},
        )


@csrf_exempt
@require_POST
def generate_quiz(request):
    try:
        data = json.loads(request.body)
        learning_path_id = data.get("learning_path_id")

        if not learning_path_id:
            return JsonResponse(
                {"success": False, "error": "ID du parcours manquant"}, status=400
            )

        learning_path = get_object_or_404(LearningPath, id=learning_path_id)

        # Préparer les données pour l'API Flask
        api_data = {
            "learning_path": {
                "language": learning_path.language,
                "level": learning_path.level,
                "modules": learning_path.modules,
            }
        }

        # Appeler l'API Flask
        flask_api_url = os.environ.get("FLASK_API_URL", "http://localhost:5000")
        response = requests.post(f"{flask_api_url}/api/generate-quiz", json=api_data)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                quiz_data = result.get("quiz")

                # Créer le quiz dans la base de données
                quiz = Quiz.objects.create(
                    learning_path=learning_path,
                    title=quiz_data["title"],
                    description=quiz_data["description"],
                    passing_score=quiz_data["passing_score"],
                )

                # Créer les questions et réponses
                for q_data in quiz_data["questions"]:
                    question = Question.objects.create(
                        quiz=quiz, text=q_data["text"], points=q_data["points"]
                    )

                    for a_data in q_data["answers"]:
                        Answer.objects.create(
                            question=question,
                            text=a_data["text"],
                            is_correct=a_data["is_correct"],
                        )

                return JsonResponse(
                    {
                        "success": True,
                        "quiz_id": quiz.id,
                        "message": "Quiz généré avec succès",
                    }
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "error": result.get(
                            "error", "Erreur lors de la génération du quiz"
                        ),
                    },
                    status=500,
                )
        else:
            return JsonResponse(
                {"success": False, "error": "Erreur de communication avec l'API"},
                status=500,
            )

    except Exception as e:
        logger.error(f"Erreur dans generate_quiz: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
