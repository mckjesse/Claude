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

TIMESTAMPS = ("created_at", "updated_at")


# ---------------------------------------------------------------------------
# Inlines shown on the Opportunity detail page
# ---------------------------------------------------------------------------
class QuoteInline(admin.TabularInline):
    model = Quote
    extra = 0
    fields = (
        "revision_number",
        "quote_reference",
        "quoted_value_ex_gst",
        "quoted_margin_percent",
        "quote_status",
        "submission_date",
    )
    show_change_link = True
    ordering = ("-revision_number",)


class FollowUpTaskInline(admin.TabularInline):
    model = FollowUpTask
    extra = 0
    fields = (
        "subject",
        "task_type",
        "priority",
        "status",
        "due_date",
        "assigned_to_user",
    )
    show_change_link = True
    autocomplete_fields = ("assigned_to_user",)
    ordering = ("due_date",)


class ActivityLogInline(admin.TabularInline):
    model = ActivityLog
    extra = 0
    fields = ("activity_type", "description", "created_by_user", "created_at")
    readonly_fields = ("activity_type", "description", "created_by_user", "created_at")
    can_delete = False
    show_change_link = False
    ordering = ("-created_at",)

    def has_add_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company_type",
        "account_tier",
        "margin_quality",
        "account_owner",
        "suburb",
        "state",
        "status",
    )
    list_filter = ("company_type", "status", "state", "account_tier", "margin_quality")
    search_fields = ("name", "primary_email", "primary_phone", "suburb")
    autocomplete_fields = ("account_owner",)
    readonly_fields = TIMESTAMPS
    fieldsets = (
        (None, {"fields": ("name", "company_type", "status")}),
        ("Contact details", {"fields": ("primary_phone", "primary_email", "website")}),
        ("Address", {"fields": ("address", "suburb", "state")}),
        (
            "Account Management",
            {
                "fields": (
                    "account_tier",
                    "margin_quality",
                    "account_owner",
                    "last_contact_date",
                    "next_contact_date",
                    "relationship_notes",
                )
            },
        ),
        ("Notes", {"fields": ("notes",)}),
        ("Timestamps", {"fields": TIMESTAMPS, "classes": ("collapse",)}),
    )


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "company",
        "role_title",
        "email",
        "mobile",
        "status",
    )
    list_filter = ("status", "preferred_contact_method", "company__company_type")
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "mobile",
        "company__name",
        "role_title",
    )
    autocomplete_fields = ("company",)
    readonly_fields = TIMESTAMPS
    fieldsets = (
        (None, {"fields": ("company", "first_name", "last_name", "role_title", "status")}),
        ("Contact details", {"fields": ("email", "phone", "mobile", "preferred_contact_method")}),
        ("Notes", {"fields": ("notes",)}),
        ("Timestamps", {"fields": TIMESTAMPS, "classes": ("collapse",)}),
    )


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------
@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "project_name",
        "project_code",
        "company",
        "stage",
        "status",
        "estimator",
        "assigned_user",
        "estimated_contract_value",
        "submission_due_date",
    )
    list_filter = (
        "stage",
        "status",
        "sector",
        "tender_type",
        "opportunity_source",
    )
    search_fields = (
        "project_name",
        "project_code",
        "company__name",
        "site_suburb",
        "scope_summary",
    )
    autocomplete_fields = (
        "company",
        "primary_contact",
        "estimator",
        "assigned_user",
    )
    date_hierarchy = "submission_due_date"
    readonly_fields = TIMESTAMPS
    inlines = [QuoteInline, FollowUpTaskInline, ActivityLogInline]

    fieldsets = (
        (
            "Project",
            {
                "fields": (
                    "project_name",
                    "project_code",
                    "company",
                    "primary_contact",
                    "site_suburb",
                )
            },
        ),
        (
            "Assignment",
            {"fields": ("estimator", "assigned_user")},
        ),
        (
            "Classification",
            {
                "fields": (
                    "sector",
                    "tender_type",
                    "opportunity_source",
                    "stage",
                    "status",
                )
            },
        ),
        (
            "Pricing",
            {
                "fields": (
                    "estimated_contract_value",
                    "estimated_margin_percent",
                    "probability_percent",
                    "final_awarded_value",
                )
            },
        ),
        (
            "Dates",
            {
                "fields": (
                    "submission_due_date",
                    "submission_date",
                    "expected_award_date",
                )
            },
        ),
        (
            "Scope",
            {
                "fields": (
                    "scope_summary",
                    "inclusions_summary",
                    "exclusions_summary",
                    "notes",
                )
            },
        ),
        ("Timestamps", {"fields": TIMESTAMPS, "classes": ("collapse",)}),
    )


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------
@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = (
        "opportunity",
        "revision_number",
        "quote_reference",
        "quoted_value_ex_gst",
        "quoted_margin_percent",
        "quote_status",
        "submission_date",
    )
    list_filter = ("quote_status",)
    search_fields = (
        "quote_reference",
        "opportunity__project_name",
        "opportunity__company__name",
    )
    autocomplete_fields = ("opportunity",)
    readonly_fields = TIMESTAMPS
    date_hierarchy = "submission_date"
    fieldsets = (
        (None, {"fields": ("opportunity", "revision_number", "quote_reference", "quote_status")}),
        (
            "Pricing",
            {
                "fields": (
                    "quoted_value_ex_gst",
                    "quoted_margin_percent",
                    "discount_percent",
                )
            },
        ),
        ("Dates", {"fields": ("submission_date", "validity_date")}),
        ("Text", {"fields": ("assumptions", "exclusions", "internal_notes")}),
        ("Timestamps", {"fields": TIMESTAMPS, "classes": ("collapse",)}),
    )


# ---------------------------------------------------------------------------
# Follow-up task
# ---------------------------------------------------------------------------
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
        "completed_at",
    )
    list_filter = ("task_type", "priority", "status")
    search_fields = (
        "subject",
        "details",
        "opportunity__project_name",
        "opportunity__company__name",
    )
    autocomplete_fields = ("opportunity", "related_quote", "assigned_to_user")
    date_hierarchy = "due_date"
    readonly_fields = TIMESTAMPS + ("completed_at",)
    fieldsets = (
        (None, {"fields": ("opportunity", "related_quote", "subject", "details")}),
        (
            "Assignment",
            {
                "fields": (
                    "assigned_to_user",
                    "task_type",
                    "priority",
                    "status",
                )
            },
        ),
        ("Schedule", {"fields": ("due_date", "due_time", "completed_at")}),
        ("Timestamps", {"fields": TIMESTAMPS, "classes": ("collapse",)}),
    )


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------
@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "opportunity",
        "activity_type",
        "entity_type",
        "description",
        "created_by_user",
    )
    list_filter = ("activity_type", "entity_type")
    search_fields = (
        "description",
        "opportunity__project_name",
        "opportunity__company__name",
    )
    autocomplete_fields = ("opportunity", "created_by_user")
    date_hierarchy = "created_at"
    readonly_fields = (
        "opportunity",
        "entity_type",
        "entity_id",
        "activity_type",
        "description",
        "created_by_user",
        "created_at",
    )

    def has_add_permission(self, request):
        # Activity log is written by the service layer, never by hand.
        return False


# ---------------------------------------------------------------------------
# Loss reason
# ---------------------------------------------------------------------------
@admin.register(LossReason)
class LossReasonAdmin(admin.ModelAdmin):
    list_display = (
        "opportunity",
        "reason_category",
        "competitor_name",
        "recorded_at",
    )
    list_filter = ("reason_category",)
    search_fields = (
        "opportunity__project_name",
        "opportunity__company__name",
        "competitor_name",
    )
    autocomplete_fields = ("opportunity",)
    readonly_fields = ("recorded_at",)
    fieldsets = (
        (None, {"fields": ("opportunity", "reason_category", "competitor_name")}),
        ("Detail", {"fields": ("reason_detail", "price_gap_notes")}),
        ("Timestamps", {"fields": ("recorded_at",), "classes": ("collapse",)}),
    )
