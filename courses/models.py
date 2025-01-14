from django.db import models

# Create your models here.


class Course(models.Model):
    titre = models.CharField(max_length=255)
    description = models.TextField()
    lien = models.URLField()
    contenu_text = models.TextField()
    lien_video = models.URLField(blank=True)
    categories = models.JSONField(default=list)
    niveau = models.CharField(max_length=50)
    duree = models.CharField(max_length=50)
    source = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)