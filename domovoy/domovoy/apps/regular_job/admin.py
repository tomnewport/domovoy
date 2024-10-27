from django.contrib import admin

from domovoy.apps.regular_job.models import RegularJobInstance, RegularJobDefinition


@admin.register(RegularJobInstance)
class RegularJobInstanceAdmin(admin.ModelAdmin):
    pass


@admin.register(RegularJobDefinition)
class RegularJobDefinition(admin.ModelAdmin):
    pass
