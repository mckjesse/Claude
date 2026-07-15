from datetime import time as dtime

from django.utils import timezone
from rest_framework import serializers

from apps.users.models import AppUser

from .models import (
    ActivityLog,
    Company,
    Contact,
    FollowUpTask,
    LossReason,
    Opportunity,
    Quote,
)

# ---------------------------------------------------------------------------
# Minimal (nested, read-only) serializers
# ---------------------------------------------------------------------------
class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = ("id", "username", "display_name", "role")
        read_only_fields = fields


class CompanyMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ("id", "name", "company_type", "status")
        read_only_fields = fields


class CompanyForOpportunitySerializer(CompanyMinimalSerializer):
    """Minimal company summary plus contact details.

    Used by OpportunitySerializer.company_detail so the opportunity page
    can render the builder/client name and contact details without an
    extra request. Other consumers of CompanyMinimalSerializer keep the
    narrower shape.
    """

    class Meta(CompanyMinimalSerializer.Meta):
        fields = CompanyMinimalSerializer.Meta.fields + (
            "primary_email",
            "primary_phone",
        )
        read_only_fields = fields


class ContactMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ("id", "first_name", "last_name", "role_title", "email")
        read_only_fields = fields


class OpportunityMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = ("id", "project_name", "project_code", "stage", "status")
        read_only_fields = fields


class OpportunitySummarySerializer(serializers.ModelSerializer):
    """
    Canonical nested summary of an Opportunity when referenced from a
    related model (follow-up, quote, activity log, loss reason).

    Shape:
        {
            "id": 7,
            "project_name": "ARB Global HQ",
            "project_id": "PRJ-1042",      # aliased from project_code
            "company_name": "Acme Builders"
        }

    Requires the consumer viewset to select_related("opportunity__company")
    so ``company_name`` is read from the joined row with no extra query.
    """

    project_id = serializers.CharField(source="project_code", read_only=True)
    company_name = serializers.CharField(
        source="company.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Opportunity
        fields = ("id", "project_name", "project_id", "company_name")
        read_only_fields = fields


class LossReasonSummarySerializer(serializers.ModelSerializer):
    """
    Embedded view of a LossReason, used inline on an Opportunity so the
    frontend can render loss-reason reporting without an extra request.
    """

    reason_label = serializers.CharField(
        source="get_reason_category_display", read_only=True
    )

    class Meta:
        model = LossReason
        fields = (
            "reason_category",
            "reason_label",
            "reason_detail",
            "competitor_name",
            "price_gap_notes",
            "recorded_at",
        )
        read_only_fields = fields


class OpportunityForFollowUpSerializer(OpportunityMinimalSerializer):
    """Minimal opportunity summary plus the parent company name.

    Used by FollowUpTaskSerializer so the frontend can render a task row
    with project + builder name without an extra request. Requires the
    viewset queryset to ``select_related("opportunity__company")`` to
    avoid an N+1 — already in place on FollowUpTaskViewSet.
    """

    company_name = serializers.CharField(
        source="company.name", read_only=True, allow_null=True
    )

    class Meta(OpportunityMinimalSerializer.Meta):
        fields = OpportunityMinimalSerializer.Meta.fields + ("company_name",)
        read_only_fields = fields


class QuoteMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = (
            "id",
            "revision_number",
            "quote_reference",
            "quoted_value_ex_gst",
            "quote_status",
            "submission_date",
        )
        read_only_fields = fields


class FollowUpTaskMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowUpTask
        fields = (
            "id",
            "subject",
            "due_date",
            "due_time",
            "status",
            "priority",
            "task_type",
        )
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Full serializers
# ---------------------------------------------------------------------------
class CompanySerializer(serializers.ModelSerializer):
    account_owner_detail = UserMinimalSerializer(
        source="account_owner", read_only=True
    )

    class Meta:
        model = Company
        fields = "__all__"


class ContactSerializer(serializers.ModelSerializer):
    company_detail = CompanyMinimalSerializer(source="company", read_only=True)

    class Meta:
        model = Contact
        fields = "__all__"


class OpportunitySerializer(serializers.ModelSerializer):
    # project_id is a read-only JSON alias for project_code — the DB
    # column name stays project_code to avoid collision with Django's
    # integer id. Writes still use project_code.
    project_id = serializers.CharField(source="project_code", read_only=True)
    is_archived = serializers.SerializerMethodField()

    company_detail = CompanyForOpportunitySerializer(source="company", read_only=True)
    primary_contact_detail = ContactMinimalSerializer(
        source="primary_contact", read_only=True
    )
    estimator_detail = UserMinimalSerializer(source="estimator", read_only=True)
    assigned_user_detail = UserMinimalSerializer(
        source="assigned_user", read_only=True
    )
    latest_quote = serializers.SerializerMethodField()
    next_followup = serializers.SerializerMethodField()

    # Loss reason exposed inline so the frontend can group lost
    # opportunities by category without a second request. Both fields
    # are null when no LossReason exists for this opportunity.
    #   loss_reason        — category key (e.g. "price") for grouping
    #   loss_reason_detail — full nested summary with the display label
    loss_reason = serializers.SerializerMethodField()
    loss_reason_detail = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = "__all__"

    # --- computed fields -------------------------------------------------
    def get_latest_quote(self, obj):
        # Iterates the prefetched `quotes` relation; no extra query.
        latest = max(
            obj.quotes.all(),
            key=lambda q: q.revision_number,
            default=None,
        )
        return QuoteMinimalSerializer(latest).data if latest else None

    def get_next_followup(self, obj):
        active_statuses = (
            FollowUpTask.Status.PENDING,
            FollowUpTask.Status.IN_PROGRESS,
        )
        active = [t for t in obj.tasks.all() if t.status in active_statuses]
        if not active:
            return None
        active.sort(key=lambda t: (t.due_date, t.due_time or dtime.min))
        return FollowUpTaskMinimalSerializer(active[0]).data

    def get_loss_reason(self, obj):
        # hasattr() correctly returns False for reverse OneToOne when no
        # LossReason row exists — Django's RelatedObjectDoesNotExist
        # extends AttributeError precisely for this purpose.
        if not hasattr(obj, "loss_reason"):
            return None
        return obj.loss_reason.reason_category

    def get_loss_reason_detail(self, obj):
        if not hasattr(obj, "loss_reason"):
            return None
        return LossReasonSummarySerializer(obj.loss_reason).data

    # --- validation ------------------------------------------------------
    def get_is_archived(self, obj):
        return obj.archived_at is not None

    def validate_probability_percent(self, value):
        if value is None:
            return value
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Must be between 0 and 100."
            )
        return value

    def validate(self, attrs):
        instance = self.instance
        current_stage = getattr(instance, "stage", None) if instance else None
        new_stage = attrs.get("stage", current_stage)
        final_value = attrs.get(
            "final_awarded_value",
            getattr(instance, "final_awarded_value", None) if instance else None,
        )

        # Guard 1: you cannot freely PATCH out of a terminal stage.
        # The only way back is through the explicit reopen action.
        _TERMINAL = {Opportunity.Stage.WON, Opportunity.Stage.LOST}
        if (
            current_stage in _TERMINAL
            and new_stage != current_stage
        ):
            raise serializers.ValidationError(
                {
                    "stage": (
                        f"This opportunity is {current_stage}. "
                        "Use POST /api/opportunities/{id}/reopen/ to "
                        "reactivate it."
                    )
                }
            )

        # Guard 2: entering won requires final_awarded_value.
        if new_stage == Opportunity.Stage.WON and final_value is None:
            raise serializers.ValidationError(
                {"final_awarded_value": "Required when stage is 'won'."}
            )

        # Guard 3: entering lost must go through mark_lost so a
        # LossReason is recorded atomically.
        if new_stage == Opportunity.Stage.LOST:
            has_reason = instance is not None and hasattr(
                instance, "loss_reason"
            )
            if not has_reason:
                raise serializers.ValidationError(
                    {
                        "stage": (
                            "An opportunity can only be moved to 'lost' via "
                            "POST /api/opportunities/{id}/mark_lost/ — a "
                            "loss reason must be recorded at the same time."
                        )
                    }
                )

        # Terminal stages always imply closed status.
        if new_stage in _TERMINAL:
            attrs["status"] = Opportunity.Status.CLOSED

        return attrs


class QuoteSerializer(serializers.ModelSerializer):
    # Writable opportunity stays a plain FK id. Frontends link to the
    # parent opportunity via the `opportunity` value directly.
    opportunity_detail = OpportunitySummarySerializer(
        source="opportunity", read_only=True
    )
    # Friendly aliases for the frontend:
    # ``value``        — read-only alias for ``quoted_value_ex_gst``
    # ``submitted_at`` — read-only alias for ``submission_date``
    value = serializers.DecimalField(
        source="quoted_value_ex_gst",
        max_digits=14,
        decimal_places=2,
        read_only=True,
    )
    submitted_at = serializers.DateField(source="submission_date", read_only=True)

    class Meta:
        model = Quote
        fields = "__all__"

    def validate_revision_number(self, value):
        if value < 1:
            raise serializers.ValidationError("Must be a positive integer (>= 1).")
        return value


class FollowUpTaskSerializer(serializers.ModelSerializer):
    # Writable opportunity stays a plain FK id (frontend uses it directly
    # for routing and cache keys). The nested summary lives beside it.
    opportunity_detail = OpportunitySummarySerializer(
        source="opportunity", read_only=True
    )
    assigned_to_user_detail = UserMinimalSerializer(
        source="assigned_to_user", read_only=True
    )
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpTask
        fields = "__all__"
        # The model FK already enforces non-null; being explicit keeps the
        # rule visible in the serializer as the spec requires.
        extra_kwargs = {
            "assigned_to_user": {"required": True, "allow_null": False},
        }

    def get_is_overdue(self, obj):
        if obj.status in (
            FollowUpTask.Status.COMPLETED,
            FollowUpTask.Status.CANCELLED,
        ):
            return False
        return obj.due_date < timezone.localdate()

    def update(self, instance, validated_data):
        # Auto-stamp completed_at when transitioning to completed.
        new_status = validated_data.get("status", instance.status)
        incoming_completed_at = validated_data.get("completed_at")
        if (
            new_status == FollowUpTask.Status.COMPLETED
            and not incoming_completed_at
            and not instance.completed_at
        ):
            validated_data["completed_at"] = timezone.now()
        return super().update(instance, validated_data)


class ActivityLogSerializer(serializers.ModelSerializer):
    opportunity_detail = OpportunitySummarySerializer(
        source="opportunity", read_only=True
    )
    created_by_user_detail = UserMinimalSerializer(
        source="created_by_user", read_only=True
    )

    class Meta:
        model = ActivityLog
        fields = "__all__"
        extra_kwargs = {
            # Sensible defaults so the frontend can POST a note with just
            # {"opportunity": <id>, "description": "..."} and everything
            # else fills in automatically.
            "entity_type": {"default": "opportunity"},
            "activity_type": {"default": "note"},
            "entity_id": {"required": False},
            "created_by_user": {"required": False},
        }


class LossReasonSerializer(serializers.ModelSerializer):
    opportunity_detail = OpportunitySummarySerializer(
        source="opportunity", read_only=True
    )

    class Meta:
        model = LossReason
        fields = "__all__"


# ---------------------------------------------------------------------------
# Custom action payload serializers
# ---------------------------------------------------------------------------
class MarkWonSerializer(serializers.Serializer):
    final_awarded_value = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=0
    )


class MarkLostSerializer(serializers.Serializer):
    reason_category = serializers.ChoiceField(choices=LossReason.Category.choices)
    reason_detail = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    competitor_name = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    price_gap_notes = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
