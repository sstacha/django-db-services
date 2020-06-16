from django.db import models
from django.conf import settings


def get_connection_choices():
    return [
        (key, key)
        for key in list(settings.DATABASES)
    ]


class Endpoint(models.Model):
    # NOTE: to run makemigrations or migrations add the --skip-checks to prevent errors on urls.py when updating this
    #   model
    connection_name = models.CharField(max_length=255, choices=get_connection_choices())
    path = models.CharField(max_length=800, unique=True)
    get_statement = models.TextField(max_length=2000, null=True, blank=True)
    post_statement = models.TextField(max_length=2000, null=True, blank=True)
    put_statement = models.TextField(max_length=2000, null=True, blank=True)
    delete_statement = models.TextField(max_length=2000, null=True, blank=True)
    notes = models.TextField(max_length=2000, null=True, blank=True)
    is_disabled = models.BooleanField(default=False)
    # modified_by = models.CharField(max_length=255, null=True, blank=True)
    # modified_date = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.path
