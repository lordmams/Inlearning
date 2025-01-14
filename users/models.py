from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    NIVEAU_CHOICES = [
        ('DEBUTANT', 'Débutant'),
        ('INTERMEDIAIRE', 'Intermédiaire'),
        ('AVANCE', 'Avancé'),
    ]
    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES)
    centres_interet = models.JSONField(default=list)
    domaines_etude = models.JSONField(default=list)
    description = models.TextField(blank=True)