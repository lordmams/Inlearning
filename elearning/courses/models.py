from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
# courses/models.py
from django.db import models
from users.models import Person


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom de la catégorie")
    description = models.TextField(blank=True, verbose_name="Description")
    icon = models.CharField(
        max_length=50, blank=True, verbose_name="Icône (classe Bootstrap)"
    )

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(max_length=200, verbose_name="Titre du cours")
    description = models.TextField(verbose_name="Description")
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="courses",
        verbose_name="Catégorie",
    )
    instructor = models.CharField(max_length=100, verbose_name="Instructeur")
    duration = models.PositiveIntegerField(verbose_name="Durée (en heures)")
    difficulty_choices = [
        ("beginner", "Débutant"),
        ("intermediate", "Intermédiaire"),
        ("advanced", "Avancé"),
    ]
    difficulty = models.CharField(
        max_length=20, choices=difficulty_choices, verbose_name="Niveau de difficulté"
    )
    image = models.ImageField(
        upload_to="course_images", blank=True, null=True, verbose_name="Image du cours"
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, verbose_name="Prix"
    )
    is_free = models.BooleanField(default=False, verbose_name="Gratuit")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Date de création"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Date de mise à jour")
    learning_mode_choices = [
        ("video", "Vidéo"),
        ("text", "Support de cours écrit"),
        ("practice", "Learning by doing"),
    ]
    learning_mode = models.CharField(
        max_length=20,
        choices=learning_mode_choices,
        verbose_name="Mode d'apprentissage",
    )

    # Nouveaux champs pour le format JSON
    source_url = models.URLField(blank=True, verbose_name="URL source du cours")
    course_link = models.URLField(blank=True, verbose_name="Lien vers le cours")

    # Contenus structurés
    paragraphs = models.JSONField(
        default=list, blank=True, verbose_name="Paragraphes de contenu"
    )
    content_lists = models.JSONField(
        default=list, blank=True, verbose_name="Listes de contenu"
    )
    examples = models.JSONField(
        default=list, blank=True, verbose_name="Exemples de code"
    )
    main_text = models.TextField(blank=True, verbose_name="Texte principal")
    video_link = models.URLField(blank=True, verbose_name="Lien vidéo principal")

    # Métadonnées JSON
    json_categories = models.JSONField(
        default=list, blank=True, verbose_name="Catégories JSON"
    )
    duration_text = models.CharField(
        max_length=100, blank=True, verbose_name="Durée (format texte)"
    )
    embedding_vector = models.JSONField(
        default=list, blank=True, verbose_name="Vecteur d'embedding"
    )

    class Meta:
        verbose_name = "Cours"
        verbose_name_plural = "Cours"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def to_elasticsearch_format(self):
        """
        Convertit le cours au format JSON attendu par Elasticsearch
        """
        return {
            "url": self.source_url or self.course_link or "",
            "cours": {
                "id": str(self.id),
                "titre": self.title,
                "description": self.description,
                "lien": self.course_link or "",
                "contenus": {
                    "paragraphs": self.paragraphs,
                    "lists": self.content_lists,
                    "examples": self.examples,
                    "texte": self.main_text,
                    "lienVideo": self.video_link,
                },
                "categories": (
                    self.json_categories or [self.category.name]
                    if self.category
                    else []
                ),
                "niveau": self.get_difficulty_display(),
                "duree": self.duration_text or f"{self.duration} heures",
                "vecteur_embedding": self.embedding_vector,
            },
        }


class Enrollment(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Utilisateur",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Cours",
    )
    enrolled_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Date d'inscription"
    )
    progress = models.PositiveIntegerField(default=0, verbose_name="Progression (%)")
    completed = models.BooleanField(default=False, verbose_name="Terminé")

    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        unique_together = ["user", "course"]

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"


class Lesson(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="lessons", verbose_name="Cours"
    )
    title = models.CharField(max_length=200, verbose_name="Titre de la leçon")
    content = models.TextField(verbose_name="Contenu")
    order = models.PositiveIntegerField(default=1, verbose_name="Ordre")
    video_url = models.URLField(blank=True, null=True, verbose_name="URL de la vidéo")

    class Meta:
        verbose_name = "Leçon"
        verbose_name_plural = "Leçons"
        ordering = ["course", "order"]
        unique_together = ["course", "order"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class LearningPath(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="learning_paths",
        verbose_name="Utilisateur",
    )
    language = models.CharField(max_length=50, verbose_name="Langage")
    level = models.IntegerField(verbose_name="Niveau")
    interests = models.JSONField(verbose_name="Centres d'intérêt")
    modules = models.JSONField(verbose_name="Modules")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Date de création"
    )

    class Meta:
        verbose_name = "Parcours d'apprentissage"
        verbose_name_plural = "Parcours d'apprentissage"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Parcours {self.language} - {self.user.username}"


class Quiz(models.Model):
    learning_path = models.ForeignKey(
        LearningPath, on_delete=models.CASCADE, related_name="quizzes"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    passing_score = models.IntegerField(
        default=70, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Quiz pour {self.learning_path.language} - {self.title}"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.IntegerField(default=0)
    points = models.IntegerField(default=1)

    def __str__(self):
        return f"Question {self.order}: {self.text[:50]}..."


class Answer(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="answers"
    )
    text = models.TextField()
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"Réponse: {self.text[:50]}..."


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Tentative de {self.user.username} pour {self.quiz.title}"


class UserAnswer(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.CASCADE, related_name="user_answers"
    )
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    is_correct = models.BooleanField()

    def __str__(self):
        return (
            f"Réponse de {self.attempt.user.username} pour {self.question.text[:50]}..."
        )


class ImportLog(models.Model):
    """Modèle pour tracer les importations de cours"""

    STATUS_CHOICES = [
        ("pending", "En attente"),
        ("processing", "En cours"),
        ("completed", "Terminé"),
        ("error", "Erreur"),
    ]

    filename = models.CharField(max_length=255, verbose_name="Nom du fichier")
    file_path = models.TextField(verbose_name="Chemin du fichier")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField(verbose_name="Démarré à")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Terminé à")
    imported_count = models.IntegerField(default=0, verbose_name="Nombre importés")
    updated_count = models.IntegerField(default=0, verbose_name="Nombre mis à jour")
    error_count = models.IntegerField(default=0, verbose_name="Nombre d'erreurs")
    error_message = models.TextField(blank=True, verbose_name="Message d'erreur")
    result_data = models.JSONField(
        null=True, blank=True, verbose_name="Données de résultat"
    )

    class Meta:
        verbose_name = "Log d'importation"
        verbose_name_plural = "Logs d'importation"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.filename} - {self.get_status_display()}"

    @property
    def duration(self):
        """Calcule la durée de traitement"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
