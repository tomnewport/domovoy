from django.contrib import admin
from domovoy.apps.dmv_home.models import Home, Membership, Holiday


@admin.register(Home)
class HomeAdmin(admin.ModelAdmin):
    pass


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    pass


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    pass
