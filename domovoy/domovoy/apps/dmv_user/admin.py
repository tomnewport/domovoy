from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from domovoy.apps.dmv_user.models import DmvUser


@admin.register(DmvUser)
class UserAdmin(UserAdmin):
    exclude = ("email",)
    list_display = ("username", "email", "name_short", "name_full", "is_staff")
    list_filter = ("is_staff", "is_superuser", "name_short", "name_full", "is_active", "groups")
    search_fields = ("username", "name_short", "name_full",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Identity"),
            {
                "fields": (
                    "name_short",
                    "name_full",
                ),
            },
        ),
        (
            _("Security"),
            {
                "fields": (
                    "email_verified",
                ),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
