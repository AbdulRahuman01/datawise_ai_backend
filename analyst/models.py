from django.db import models

# Create your models here.
from django.contrib.auth.models import User


class Movie(models.Model):
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100)
    rating = models.FloatField()
    release_year = models.IntegerField()

    def __str__(self):
        return self.title


class Subscription(models.Model):
    PLAN_CHOICES = (
        ("Basic", "Basic"),
        ("Standard", "Standard"),
        ("Premium", "Premium"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    start_date = models.DateField()

    def __str__(self):
        return f"{self.user.username} - {self.plan}"
