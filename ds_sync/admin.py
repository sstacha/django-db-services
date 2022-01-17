from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportActionModelAdmin

from .models import SyncConfiguration, SyncRun, SyncAlert


class SyncConfigurationResource(resources.ModelResource):
    class Meta:
        model = SyncConfiguration
        exclude = ('id', )
        skip_unchanged = True


class ChannelFilter(admin.SimpleListFilter):
    title = 'channel'
    parameter_name = 'channel'

    def lookups(self, request, model_admin):
        return SyncConfiguration.channels.tag_model.objects.values_list('id', 'name')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(channels__name_iexact=self.value())


# Register your models here.
@admin.register(SyncConfiguration)
class SyncConfigurationAdmin(ImportExportActionModelAdmin):
    search_fields = ('table_name', )
    list_display = ('from_connection_name', 'to_connection_name', 'table_name', 'channel', 'is_active')
    list_filter = ('from_connection_name', 'to_connection_name', 'table_name', ChannelFilter)
    # readonly_fields = ('modified_by', 'modified_date',)
    # save_as = True

    def channel(self, obj):
        return ", ".join([str(p) for p in obj.channels.all()])


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    search_fields = ('start_date', 'end_date')
    list_display = ('sync', 'start_date', 'end_date', 'has_succeeded')
    list_filter = ('sync__from_connection_name', 'sync__to_connection_name', 'sync__table_name')
    readonly_fields = ('start_date', 'end_date')


@admin.register(SyncAlert)
class SyncAlertAdmin(admin.ModelAdmin):
    search_fields = ('alert_email_list',)
    list_display = ('sync', 'last_alert_date', 'after_failure_cnt', 'email_list')
    list_filter = ('sync__from_connection_name', 'sync__to_connection_name', 'sync__table_name')
