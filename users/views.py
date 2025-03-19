from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from .models import (
    Person, Preferences, Interest, AcademicBackground, FieldOfStudy,
    ProfessionalBackground, Job, Goals, ShortTermGoal, LongTermGoal
)
from .forms import (
    PersonForm, PreferencesForm, InterestFormSet, AcademicBackgroundForm,
    FieldOfStudyFormSet, ProfessionalBackgroundForm, JobFormSet,
    GoalsForm, ShortTermGoalFormSet, LongTermGoalFormSet
)


class UserProfileView(View):
    template_name = 'user_profile_form.html'

    def get(self, request, pk=None):
        # Si un pk est fourni, nous récupérons un profil existant, sinon nous créons un nouveau
        if pk:
            try:
                person = Person.objects.get(pk=pk)
                person_form = PersonForm(instance=person)
                
                # Récupérer ou créer des instances liées
                preferences, _ = Preferences.objects.get_or_create(person=person)
                preferences_form = PreferencesForm(instance=preferences)
                interest_formset = InterestFormSet(instance=preferences)
                
                academic_background, _ = AcademicBackground.objects.get_or_create(person=person)
                academic_form = AcademicBackgroundForm(instance=academic_background)
                field_of_study_formset = FieldOfStudyFormSet(instance=academic_background)
                
                professional_background, _ = ProfessionalBackground.objects.get_or_create(person=person)
                professional_form = ProfessionalBackgroundForm(instance=professional_background)
                job_formset = JobFormSet(instance=professional_background)
                
                goals, _ = Goals.objects.get_or_create(person=person)
                goals_form = GoalsForm(instance=goals)
                short_term_goal_formset = ShortTermGoalFormSet(instance=goals)
                long_term_goal_formset = LongTermGoalFormSet(instance=goals)
            
            except Person.DoesNotExist:
                return redirect('create_profile')
        else:
            # Formulaires vides pour un nouveau profil
            person_form = PersonForm()
            preferences_form = PreferencesForm()
            interest_formset = InterestFormSet()
            academic_form = AcademicBackgroundForm()
            field_of_study_formset = FieldOfStudyFormSet()
            professional_form = ProfessionalBackgroundForm()
            job_formset = JobFormSet()
            goals_form = GoalsForm()
            short_term_goal_formset = ShortTermGoalFormSet()
            long_term_goal_formset = LongTermGoalFormSet()

        return render(request, self.template_name, {
            'person_form': person_form,
            'preferences_form': preferences_form,
            'interest_formset': interest_formset,
            'academic_form': academic_form,
            'field_of_study_formset': field_of_study_formset,
            'professional_form': professional_form,
            'job_formset': job_formset,
            'goals_form': goals_form,
            'short_term_goal_formset': short_term_goal_formset,
            'long_term_goal_formset': long_term_goal_formset,
        })

    @transaction.atomic
    def post(self, request, pk=None):
        # Si un pk est fourni, nous mettons à jour un profil existant, sinon nous créons un nouveau
        if pk:
            try:
                person = Person.objects.get(pk=pk)
                person_form = PersonForm(request.POST, instance=person)
                
                preferences = Preferences.objects.get(person=person)
                preferences_form = PreferencesForm(request.POST, instance=preferences)
                interest_formset = InterestFormSet(request.POST, instance=preferences)
                
                academic_background = AcademicBackground.objects.get(person=person)
                academic_form = AcademicBackgroundForm(request.POST, instance=academic_background)
                field_of_study_formset = FieldOfStudyFormSet(request.POST, instance=academic_background)
                
                professional_background = ProfessionalBackground.objects.get(person=person)
                professional_form = ProfessionalBackgroundForm(request.POST, instance=professional_background)
                job_formset = JobFormSet(request.POST, instance=professional_background)
                
                goals = Goals.objects.get(person=person)
                goals_form = GoalsForm(request.POST, instance=goals)
                short_term_goal_formset = ShortTermGoalFormSet(request.POST, instance=goals)
                long_term_goal_formset = LongTermGoalFormSet(request.POST, instance=goals)
            
            except (Person.DoesNotExist, Preferences.DoesNotExist, 
                    AcademicBackground.DoesNotExist, ProfessionalBackground.DoesNotExist,
                    Goals.DoesNotExist):
                return redirect('create_profile')
        else:
            # Formulaires pour un nouveau profil
            person_form = PersonForm(request.POST)
            preferences_form = PreferencesForm(request.POST)
            interest_formset = InterestFormSet(request.POST)
            academic_form = AcademicBackgroundForm(request.POST)
            field_of_study_formset = FieldOfStudyFormSet(request.POST)
            professional_form = ProfessionalBackgroundForm(request.POST)
            job_formset = JobFormSet(request.POST)
            goals_form = GoalsForm(request.POST)
            short_term_goal_formset = ShortTermGoalFormSet(request.POST)
            long_term_goal_formset = LongTermGoalFormSet(request.POST)

        # Vérifier si tous les formulaires sont valides
        if (person_form.is_valid() and preferences_form.is_valid() and interest_formset.is_valid() and
                academic_form.is_valid() and field_of_study_formset.is_valid() and
                professional_form.is_valid() and job_formset.is_valid() and
                goals_form.is_valid() and short_term_goal_formset.is_valid() and
                long_term_goal_formset.is_valid()):
            
            # Sauvegarder Person
            person = person_form.save()
            
            # Sauvegarder Preferences
            preferences = preferences_form.save(commit=False)
            preferences.person = person
            preferences.save()
            interest_formset.instance = preferences
            interest_formset.save()
            
            # Sauvegarder Academic Background
            academic_background = academic_form.save(commit=False)
            academic_background.person = person
            academic_background.save()
            field_of_study_formset.instance = academic_background
            field_of_study_formset.save()
            
            # Sauvegarder Professional Background
            professional_background = professional_form.save(commit=False)
            professional_background.person = person
            professional_background.save()
            job_formset.instance = professional_background
            job_formset.save()
            
            # Sauvegarder Goals
            goals = goals_form.save(commit=False)
            goals.person = person
            goals.save()
            short_term_goal_formset.instance = goals
            short_term_goal_formset.save()
            long_term_goal_formset.instance = goals
            long_term_goal_formset.save()
            
            messages.success(request, "Profil utilisateur enregistré avec succès!")
            return redirect('profile_detail', pk=person.pk)
        else:
            # Erreurs dans les formulaires
            messages.error(request, "Il y a des erreurs dans le formulaire. Veuillez les corriger.")

        return render(request, self.template_name, {
            'person_form': person_form,
            'preferences_form': preferences_form,
            'interest_formset': interest_formset,
            'academic_form': academic_form,
            'field_of_study_formset': field_of_study_formset,
            'professional_form': professional_form,
            'job_formset': job_formset,
            'goals_form': goals_form,
            'short_term_goal_formset': short_term_goal_formset,
            'long_term_goal_formset': long_term_goal_formset,
        })


class PersonDetailView(DetailView):
    model = Person
    template_name = 'person_detail.html'
    context_object_name = 'person'


class PersonListView(ListView):
    model = Person
    template_name = 'person_list.html'
    context_object_name = 'persons'