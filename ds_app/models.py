from django.db import models
from django.conf import settings

log_level_choices = (
    (10, 'Debug'),
    (20, 'Info'),
    (30, 'Warning')
)


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
    log_level_override = models.PositiveSmallIntegerField(choices=log_level_choices, null=True, blank=True)
    log_filter_field_name = models.CharField(max_length=100, null=True, blank=True)
    log_filter_field_value = models.CharField(max_length=100, null=True, blank=True)
    # modified_by = models.CharField(max_length=255, null=True, blank=True)
    # modified_date = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        ordering = ["path"]

    def __str__(self):
        return self.path
