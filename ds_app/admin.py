from django.contrib import admin
from django.dispatch import receiver
from import_export import resources
from import_export.signals import post_import
from import_export.admin import ImportExportActionModelAdmin

from .models import Endpoint
from .utils import reload_app_urls


class EndpointResource(resources.ModelResource):
    class Meta:
        model = Endpoint
        exclude = ('id', 'modified_date')
        import_id_fields = ('path',)
        skip_unchanged = True


# hooks for clearing the urls when we import data like when we save in admin
@receiver(post_import, dispatch_uid='ds_app_import')
def _post_import(model, **kwargs):
    # model is the actual model instance which after import
    reload_app_urls()


# Register your models here.
@admin.register(Endpoint)
class EndpointAdmin(ImportExportActionModelAdmin):
    resource_class = EndpointResource
    search_fields = ('path', )
    list_display = ('path', 'connection_name', 'is_disabled')
    list_filter = ('connection_name', )
    # readonly_fields = ('modified_by', 'modified_date',)
    save_as = True

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # instance = form.save(commit=False)
        # instance.modified_by = str(request.user)[:255]
        # instance.save()
        # form.save_m2m()
        # reload_urls('ds_app.urls')
        reload_app_urls()
        # return instance

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        # reload_urls('ds_app.urls')
        reload_app_urls()
