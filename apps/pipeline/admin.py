from django.contrib import admin

from .models import (
    ActivityLog,
    Company,
    Contact,
    FollowUpTask,
    LossReason,
    Opportunity,
    Quote,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "company_type", "suburb", "state", "status")
    list_filter = ("company_type", "status", "state")
    search_fields = ("name", "primary_email", "suburb")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "company",
        "role_title",
        "status",
    )
    list_filter = ("status", "preferred_contact_method")
    search_fields = ("first_name", "last_name", "email", "company__name")
    autocomplete_fields = ("company",)


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "project_name",
        "company",
        "stage",
        "status",
        "estimator",
        "assigned_user",
        "submission_due_date",
        "estimated_contract_value",
    )
    list_filter = ("stage", "status", "sector", "tender_type")
    search_fields = ("project_name", "project_code", "company__name")
    autocomplete_fields = (
        "company",
        "primary_contact",
        "estimator",
        "assigned_user",
    )
    date_hierarchy = "submission_due_date"


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = (
        "opportunity",
        "revision_number",
        "quote_reference",
        "quoted_value_ex_gst",
        "quote_status",
        "submission_date",
    )
    list_filter = ("quote_status",)
    search_fields = ("quote_reference", "opportunity__project_name")
    autocomplete_fields = ("opportunity",)


@admin.register(FollowUpTask)
class FollowUpTaskAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "opportunity",
        "assigned_to_user",
        "task_type",
        "priority",
        "status",
        "due_date",
    )
    list_filter = ("task_type", "priority", "status")
    search_fields = ("subject", "opportunity__project_name")
    autocomplete_fields = ("opportunity", "related_quote", "assigned_to_user")
    date_hierarchy = "due_date"


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "opportunity",
        "activity_type",
        "entity_type",
        "entity_id",
        "created_by_user",
        "created_at",
    )
    list_filter = ("activity_type", "entity_type")
    search_fields = ("description", "opportunity__project_name")
    autocomplete_fields = ("opportunity", "created_by_user")
    date_hierarchy = "created_at"


@admin.register(LossReason)
class LossReasonAdmin(admin.ModelAdmin):
    list_display = (
        "opportunity",
        "reason_category",
        "competitor_name",
        "recorded_at",
    )
    list_filter = ("reason_category",)
    search_fields = ("opportunity__project_name", "competitor_name")
    autocomplete_fields = ("opportunity",)
