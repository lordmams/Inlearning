from django.contrib import admin
from django import forms
from django.db import models
import json

# Register your models here.
# courses/admin.py
from django.contrib import admin
from .models import Category, Course, Enrollment, Lesson

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    ordering = ('order',)

class CourseAdminForm(forms.ModelForm):
    """Formulaire personnalisé pour améliorer l'interface d'ajout de cours"""
    
    # Champs texte améliorés pour les contenus JSON
    paragraphs_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 6, 'placeholder': 'Un paragraphe par ligne'}),
        required=False,
        label="Paragraphes (un par ligne)",
        help_text="Entrez chaque paragraphe sur une nouvelle ligne"
    )
    
    content_lists_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Élément 1\nÉlément 2\n---\nListe 2 - Élément 1\nListe 2 - Élément 2'}),
        required=False,
        label="Listes de contenu",
        help_text="Séparez les listes par '---' et les éléments par des retours à la ligne"
    )
    
    examples_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 8, 'placeholder': 'Exemple de code 1\n---\nExemple de code 2'}),
        required=False,
        label="Exemples de code",
        help_text="Séparez les exemples par '---'"
    )
    
    categories_text = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Programmation, Python, Web'}),
        required=False,
        label="Catégories JSON",
        help_text="Catégories séparées par des virgules"
    )
    
    class Meta:
        model = Course
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'main_text': forms.Textarea(attrs={'rows': 6}),
            'duration_text': forms.TextInput(attrs={'placeholder': 'ex: 4 à 6 semaines, 20 heures'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pré-remplir les champs texte si l'objet existe
        if self.instance.pk:
            if self.instance.paragraphs:
                self.fields['paragraphs_text'].initial = '\n'.join(self.instance.paragraphs)
            
            if self.instance.content_lists:
                lists_text = []
                for lst in self.instance.content_lists:
                    if isinstance(lst, list):
                        lists_text.append('\n'.join(lst))
                self.fields['content_lists_text'].initial = '\n---\n'.join(lists_text)
            
            if self.instance.examples:
                self.fields['examples_text'].initial = '\n---\n'.join(self.instance.examples)
            
            if self.instance.json_categories:
                self.fields['categories_text'].initial = ', '.join(self.instance.json_categories)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Convertir les champs texte en JSON
        if self.cleaned_data.get('paragraphs_text'):
            paragraphs = [p.strip() for p in self.cleaned_data['paragraphs_text'].split('\n') if p.strip()]
            instance.paragraphs = paragraphs
        
        if self.cleaned_data.get('content_lists_text'):
            lists = []
            for list_text in self.cleaned_data['content_lists_text'].split('---'):
                if list_text.strip():
                    items = [item.strip() for item in list_text.strip().split('\n') if item.strip()]
                    if items:
                        lists.append(items)
            instance.content_lists = lists
        
        if self.cleaned_data.get('examples_text'):
            examples = [ex.strip() for ex in self.cleaned_data['examples_text'].split('---') if ex.strip()]
            instance.examples = examples
        
        if self.cleaned_data.get('categories_text'):
            categories = [cat.strip() for cat in self.cleaned_data['categories_text'].split(',') if cat.strip()]
            instance.json_categories = categories
        
        if commit:
            instance.save()
        return instance

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    form = CourseAdminForm
    list_display = ('title', 'category', 'instructor', 'difficulty', 'learning_mode', 'price', 'is_free', 'created_at')
    list_filter = ('category', 'difficulty', 'learning_mode', 'is_free')
    search_fields = ('title', 'instructor', 'description')
    inlines = [LessonInline]
    list_editable = ('price', 'is_free')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('title', 'description', 'category', 'instructor', 'difficulty', 'learning_mode')
        }),
        ('URLs et liens', {
            'fields': ('source_url', 'course_link', 'video_link'),
            'classes': ('collapse',)
        }),
        ('Contenu structuré', {
            'fields': ('paragraphs_text', 'content_lists_text', 'examples_text', 'main_text'),
            'classes': ('collapse',),
            'description': 'Contenu qui sera exporté vers Elasticsearch'
        }),
        ('Métadonnées', {
            'fields': ('categories_text', 'duration', 'duration_text', 'price', 'is_free'),
            'classes': ('collapse',)
        }),
        ('Média', {
            'fields': ('image',),
            'classes': ('collapse',)
        }),
        ('Données techniques (lecture seule)', {
            'fields': ('paragraphs', 'content_lists', 'examples', 'json_categories', 'embedding_vector'),
            'classes': ('collapse',),
            'description': 'Ces champs sont automatiquement générés'
        })
    )
    
    readonly_fields = ('paragraphs', 'content_lists', 'examples', 'json_categories', 'embedding_vector')
    
    actions = ['export_to_elasticsearch_format']
    
    def export_to_elasticsearch_format(self, request, queryset):
        """Action pour exporter les cours sélectionnés au format Elasticsearch"""
        courses_json = []
        for course in queryset:
            courses_json.append(course.to_elasticsearch_format())
        
        # Ici vous pouvez ajouter la logique pour envoyer vers Elasticsearch
        # ou simplement afficher le JSON
        from django.http import JsonResponse
        import json
        
        response = JsonResponse(courses_json, safe=False, json_dumps_params={'indent': 2, 'ensure_ascii': False})
        response['Content-Disposition'] = 'attachment; filename="courses_elasticsearch.json"'
        return response
    
    export_to_elasticsearch_format.short_description = "Exporter au format Elasticsearch"

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'enrolled_at', 'progress', 'completed')
    list_filter = ('completed',)
    search_fields = ('user__username', 'course__title')
    date_hierarchy = 'enrolled_at'

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order')
    list_filter = ('course',)
    search_fields = ('title', 'content', 'course__title')
    ordering = ('course', 'order')