from django.db import models


class Account(models.Model):
    name = models.CharField(unique=True, max_length=128, null=False, blank=False)
    api_key = models.CharField(max_length=256, blank=False)
    api_secret = models.CharField(max_length=256, blank=False)

    def __str__(self):
        return self.name
