from django.contrib import admin

from .models import (AcademicBackground, FieldOfStudy, Goals, Interest, Job,
                     LongTermGoal, Person, Preferences, ProfessionalBackground,
                     ShortTermGoal)


class InterestInline(admin.TabularInline):
    model = Interest
    extra = 1


class PreferencesInline(admin.StackedInline):
    model = Preferences
    extra = 0


class AcademicBackgroundInline(admin.StackedInline):
    model = AcademicBackground
    extra = 0


class ProfessionalBackgroundInline(admin.StackedInline):
    model = ProfessionalBackground
    extra = 0


class GoalsInline(admin.StackedInline):
    model = Goals
    extra = 0


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["email", "name", "age", "gender"]
    list_filter = ["gender"]
    search_fields = ["email", "name"]
    inlines = [
        PreferencesInline,
        AcademicBackgroundInline,
        ProfessionalBackgroundInline,
        GoalsInline,
    ]


@admin.register(Preferences)
class PreferencesAdmin(admin.ModelAdmin):
    inlines = [InterestInline]
    list_display = ["person", "preferred_language", "learning_mode"]


@admin.register(AcademicBackground)
class AcademicBackgroundAdmin(admin.ModelAdmin):
    list_display = ["person", "highest_academic_level"]


@admin.register(ProfessionalBackground)
class ProfessionalBackgroundAdmin(admin.ModelAdmin):
    list_display = ["person", "total_experience_years"]


class ShortTermGoalInline(admin.TabularInline):
    model = ShortTermGoal
    extra = 1


class LongTermGoalInline(admin.TabularInline):
    model = LongTermGoal
    extra = 1


@admin.register(Goals)
class GoalsAdmin(admin.ModelAdmin):
    inlines = [ShortTermGoalInline, LongTermGoalInline]
    list_display = ["person"]
