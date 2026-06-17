from django.contrib import admin

from .models import Builder, Contact

TIMESTAMPS = ("created_at", "updated_at")


class ContactInline(admin.TabularInline):
    model = Contact
    fk_name = "builder"
    extra = 0
    fields = (
        "first_name",
        "last_name",
        "role",
        "mobile",
        "email",
        "relationship_strength",
    )
    show_change_link = True


@admin.register(Builder)
class BuilderAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tier",
        "revenue_last_12_months",
        "margin_quality",
        "account_owner",
        "last_contact_date",
        "next_contact_date",
    )
    list_filter = ("tier", "margin_quality")
    search_fields = ("name",)
    autocomplete_fields = ("account_owner",)
    readonly_fields = TIMESTAMPS
    inlines = [ContactInline]
    fieldsets = (
        (None, {"fields": ("name", "tier", "margin_quality", "account_owner")}),
        ("Revenue", {"fields": ("revenue_last_12_months",)}),
        ("Engagement", {"fields": ("last_contact_date", "next_contact_date")}),
        ("Notes", {"fields": ("notes",)}),
        ("Timestamps", {"fields": TIMESTAMPS, "classes": ("collapse",)}),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "builder",
        "role",
        "mobile",
        "email",
        "relationship_strength",
    )
    list_filter = ("relationship_strength",)
    search_fields = ("first_name", "last_name", "email", "builder__name")
    autocomplete_fields = ("builder", "moved_from_builder")
    readonly_fields = TIMESTAMPS
    fieldsets = (
        (None, {"fields": ("builder", "first_name", "last_name", "role")}),
        ("Contact", {"fields": ("mobile", "email")}),
        (
            "Relationship",
            {
                "fields": (
                    "relationship_strength",
                    "last_contact_date",
                    "next_contact_date",
                    "moved_from_builder",
                )
            },
        ),
        ("Notes", {"fields": ("notes",)}),
        ("Timestamps", {"fields": TIMESTAMPS, "classes": ("collapse",)}),
    )
