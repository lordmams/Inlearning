import csv
import io
import json
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError


class CourseImportForm(forms.Form):
    file = forms.FileField(
        label="Fichier à importer",
        help_text="Sélectionnez un fichier JSON ou CSV contenant les données de cours",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    format_type = forms.ChoiceField(
        choices=[
            ("json", "JSON"),
            ("csv", "CSV"),
            ("xlsx", "Excel"),
        ],
        label="Format du fichier",
        initial="json",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    update_existing = forms.BooleanField(
        label="Mettre à jour les cours existants",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    dry_run = forms.BooleanField(
        label="Test uniquement (ne pas sauvegarder)",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_file(self):
        file = self.cleaned_data["file"]

        # Vérifier la taille du fichier (max 50MB)
        if file.size > 50 * 1024 * 1024:
            raise forms.ValidationError(
                "Le fichier est trop volumineux. Taille maximale: 50MB"
            )

        # Vérifier l'extension
        file_extension = Path(file.name).suffix.lower()
        allowed_extensions = [".json", ".csv", ".xlsx", ".xls"]

        if file_extension not in allowed_extensions:
            raise forms.ValidationError(
                f"Extension de fichier non supportée: {file_extension}. "
                f"Extensions autorisées: {', '.join(allowed_extensions)}"
            )

        return file

    def clean(self):
        cleaned_data = super().clean()
        file = cleaned_data.get("file")
        format_type = cleaned_data.get("format_type")

        if file and format_type:
            # Validation minimale : juste vérifier que le fichier est lisible
            try:
                if format_type == "json":
                    self._basic_json_validation(file)
                elif format_type == "csv":
                    self._basic_csv_validation(file)
            except Exception as e:
                raise forms.ValidationError(f"Fichier illisible: {str(e)}")

        return cleaned_data

    def _basic_json_validation(self, file):
        """Validation basique JSON - juste vérifier que c'est du JSON valide"""
        try:
            file.seek(0)
            content = file.read().decode("utf-8")
            json.loads(content)
            file.seek(0)  # Reset pour usage ultérieur
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise ValidationError(f"Fichier JSON invalide: {str(e)}")

    def _basic_csv_validation(self, file):
        """Validation basique CSV - juste vérifier que c'est du CSV lisible"""
        try:
            file.seek(0)
            content = file.read().decode("utf-8")
            # Tenter de lire au moins une ligne
            csv_reader = csv.reader(io.StringIO(content))
            next(csv_reader)  # Lire la première ligne
            file.seek(0)  # Reset pour usage ultérieur
        except (UnicodeDecodeError, csv.Error) as e:
            raise ValidationError(f"Fichier CSV invalide: {str(e)}")


class BatchActionForm(forms.Form):
    """Formulaire pour les actions par lot sur les cours"""

    ACTION_CHOICES = [
        ("activate", "Activer les cours sélectionnés"),
        ("deactivate", "Désactiver les cours sélectionnés"),
        ("delete", "Supprimer les cours sélectionnés"),
        ("export", "Exporter les cours sélectionnés"),
        ("reindex", "Réindexer dans Elasticsearch"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label="Action à effectuer",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    course_ids = forms.CharField(widget=forms.HiddenInput(), required=True)

    confirm = forms.BooleanField(
        label="Je confirme vouloir effectuer cette action",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_course_ids(self):
        course_ids = self.cleaned_data["course_ids"]
        try:
            # Convertir la chaîne d'IDs en liste d'entiers
            ids_list = [
                int(id_str.strip())
                for id_str in course_ids.split(",")
                if id_str.strip()
            ]
            if not ids_list:
                raise forms.ValidationError("Aucun cours sélectionné")
            return ids_list
        except ValueError:
            raise forms.ValidationError("IDs de cours invalides")


class CourseTemplateForm(forms.Form):
    """Formulaire pour télécharger un template de cours"""

    TEMPLATE_CHOICES = [
        ("csv", "Template CSV"),
        ("json", "Template JSON"),
        ("xlsx", "Template Excel"),
    ]

    template_type = forms.ChoiceField(
        choices=TEMPLATE_CHOICES,
        label="Type de template",
        initial="csv",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    include_examples = forms.BooleanField(
        label="Inclure des exemples de données",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_template_type(self):
        template_type = self.cleaned_data["template_type"]
        if template_type not in ["csv", "json", "xlsx"]:
            raise forms.ValidationError("Type de template invalide")
        return template_type


class ServiceMonitoringForm(forms.Form):
    """Formulaire pour configurer le monitoring des services"""

    SERVICE_TYPE_CHOICES = [
        ("django", "Django Application"),
        ("flask_api", "Flask API"),
        ("elasticsearch", "Elasticsearch"),
        ("postgres", "PostgreSQL"),
        ("redis", "Redis"),
        ("orchestration", "Python Orchestrator"),
        ("spark_master", "Spark Master"),
        ("spark_worker", "Spark Worker"),
        ("pgadmin", "PgAdmin"),
        ("consumer", "File Consumer"),
    ]

    name = forms.CharField(
        max_length=100,
        label="Nom du service",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    service_type = forms.ChoiceField(
        choices=SERVICE_TYPE_CHOICES,
        label="Type de service",
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    url = forms.URLField(
        label="URL principale du service",
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )

    health_check_url = forms.URLField(
        label="URL de vérification de santé",
        widget=forms.URLInput(attrs={"class": "form-control"}),
    )

    is_critical = forms.BooleanField(
        label="Service critique",
        required=False,
        initial=True,
        help_text="Cocher si ce service est critique pour le système",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


class AlertResolutionForm(forms.Form):
    """Formulaire pour résoudre une alerte"""

    resolution_note = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Note de résolution (optionnel)",
            }
        ),
        label="Note de résolution",
        required=False,
        max_length=500,
    )

    mark_as_resolved = forms.BooleanField(
        label="Marquer comme résolu",
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
