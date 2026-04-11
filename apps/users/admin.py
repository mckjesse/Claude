from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AppUser


@admin.register(AppUser)
class AppUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("FOXD", {"fields": ("role", "display_name")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("FOXD", {"fields": ("role", "display_name")}),
    )
    list_display = (
        "username",
        "email",
        "display_name",
        "role",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "display_name", "first_name", "last_name")
    ordering = ("username",)
