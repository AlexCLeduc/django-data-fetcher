from django.conf import settings
from django.db import models
from django.utils import timezone


class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)


class Tag(models.Model):
    name = models.CharField(max_length=250)

    def __str__(self):
        return self.name


class Book(models.Model):
    author = models.ForeignKey(
        Author, related_name="books", on_delete=models.CASCADE
    )
    title = models.CharField(max_length=250)
    tags = models.ManyToManyField(Tag)
