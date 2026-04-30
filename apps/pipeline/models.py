from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    """Abstract base that adds standard created_at / updated_at timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------
class Company(TimestampedModel):
    class Type(models.TextChoices):
        BUILDER = "builder", "Builder"
        CLIENT = "client", "Client"
        ARCHITECT = "architect", "Architect"
        PROJECT_MANAGER = "project_manager", "Project Manager"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    name = models.CharField(max_length=255)
    company_type = models.CharField(
        max_length=32, choices=Type.choices, default=Type.OTHER
    )
    primary_phone = models.CharField(max_length=50, blank=True)
    primary_email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    suburb = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Contact
# ---------------------------------------------------------------------------
class Contact(TimestampedModel):
    class PreferredContactMethod(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        MOBILE = "mobile", "Mobile"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role_title = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    mobile = models.CharField(max_length=50, blank=True)
    preferred_contact_method = models.CharField(
        max_length=16,
        choices=PreferredContactMethod.choices,
        blank=True,
    )
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


# ---------------------------------------------------------------------------
# Opportunity
# ---------------------------------------------------------------------------
class Opportunity(TimestampedModel):
    class Stage(models.TextChoices):
        LEAD = "lead", "Lead"
        INVITED = "invited", "Invited"
        PRICING = "pricing", "Pricing"
        SUBMITTED = "submitted", "Submitted"
        FOLLOW_UP = "follow_up", "Follow Up"
        NEGOTIATING = "negotiating", "Negotiating"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        WITHDRAWN = "withdrawn", "Withdrawn"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    project_name = models.CharField(max_length=255)
    # project_code is the human-facing "Project ID" displayed throughout
    # the UI (labels, reports, URLs). The internal primary key `id`
    # remains the technical identifier for foreign keys and relations.
    # Not globally unique — FOXD may price the same project to multiple
    # builders. Uniqueness is scoped to (project_code, company).
    project_code = models.CharField(max_length=100)

    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="opportunities",
    )
    primary_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_for_opportunities",
    )
    estimator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="estimating_opportunities",
    )
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_opportunities",
    )

    sector = models.CharField(max_length=100, blank=True)
    opportunity_source = models.CharField(max_length=100, blank=True)
    tender_type = models.CharField(max_length=100, blank=True)

    stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.LEAD
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.OPEN
    )

    site_suburb = models.CharField(max_length=100, blank=True)

    estimated_contract_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    estimated_margin_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    submission_due_date = models.DateField(null=True, blank=True)
    submission_date = models.DateField(null=True, blank=True)
    expected_award_date = models.DateField(null=True, blank=True)
    probability_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    scope_summary = models.TextField(blank=True)
    inclusions_summary = models.TextField(blank=True)
    exclusions_summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    final_awarded_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    # Soft delete / archive. ``archived_at is not None`` means the
    # opportunity is hidden from normal list views, dashboard and
    # reports, but the row (and all its related quotes, tasks,
    # activity logs, loss reason) is still present for audit. Call
    # the /archive/ and /restore/ actions to toggle; hard DELETE is
    # still available to directors but requires archiving first.
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archived_opportunities",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Opportunity"
        verbose_name_plural = "Opportunities"
        constraints = [
            models.UniqueConstraint(
                fields=["project_code", "company"],
                name="unique_project_code_per_company",
            ),
        ]

    def __str__(self):
        return self.project_name


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------
class Quote(TimestampedModel):
    class QuoteStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        REVISED = "revised", "Revised"
        WITHDRAWN = "withdrawn", "Withdrawn"
        ACCEPTED = "accepted", "Accepted"
        UNSUCCESSFUL = "unsuccessful", "Unsuccessful"

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name="quotes",
    )
    revision_number = models.PositiveIntegerField(default=1)
    quote_reference = models.CharField(max_length=100, blank=True)
    quoted_value_ex_gst = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    quoted_margin_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    submission_date = models.DateField(null=True, blank=True)
    validity_date = models.DateField(null=True, blank=True)
    quote_status = models.CharField(
        max_length=20,
        choices=QuoteStatus.choices,
        default=QuoteStatus.DRAFT,
    )
    assumptions = models.TextField(blank=True)
    exclusions = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["opportunity", "-revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["opportunity", "revision_number"],
                name="unique_quote_revision_per_opportunity",
            ),
        ]

    def __str__(self):
        return f"{self.opportunity.project_name} rev {self.revision_number}"


# ---------------------------------------------------------------------------
# FollowUpTask
# ---------------------------------------------------------------------------
class FollowUpTask(TimestampedModel):
    class TaskType(models.TextChoices):
        CALL = "call", "Call"
        EMAIL = "email", "Email"
        MEETING = "meeting", "Meeting"
        REMINDER = "reminder", "Reminder"
        REVIEW = "review", "Review"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    related_quote = models.ForeignKey(
        Quote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tasks",
    )
    assigned_to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="followup_tasks",
    )
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    due_date = models.DateField()
    due_time = models.TimeField(null=True, blank=True)
    priority = models.CharField(
        max_length=16, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    subject = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_followups",
    )
    completion_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["due_date", "due_time"]

    def __str__(self):
        return self.subject


# ---------------------------------------------------------------------------
# ActivityLog
# ---------------------------------------------------------------------------
class ActivityLog(models.Model):
    """
    Append-only log of events tied to an opportunity. `entity_type` and
    `entity_id` point at the specific sub-object the event concerns (quote,
    task, contact, etc.) without needing a formal generic relation.
    """

    opportunity = models.ForeignKey(
        Opportunity,
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    entity_type = models.CharField(max_length=100)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    activity_type = models.CharField(max_length=100)
    description = models.TextField()
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.activity_type} ({self.entity_type}#{self.entity_id})"


# ---------------------------------------------------------------------------
# LossReason
# ---------------------------------------------------------------------------
class LossReason(models.Model):
    class Category(models.TextChoices):
        PRICE = "price", "Price"
        SCOPE = "scope", "Scope"
        RELATIONSHIP = "relationship", "Relationship"
        TIMING = "timing", "Timing"
        CAPABILITY = "capability", "Capability"
        COMPETITOR = "competitor", "Competitor"
        CLIENT_CHANGE = "client_change", "Client Change"
        NO_DECISION = "no_decision", "No Decision"
        PROJECT_WON_OTHER = "project_won_other", "Project Won via Another Builder"
        OTHER = "other", "Other"

    opportunity = models.OneToOneField(
        Opportunity,
        on_delete=models.CASCADE,
        related_name="loss_reason",
    )
    reason_category = models.CharField(max_length=20, choices=Category.choices)
    reason_detail = models.TextField(blank=True)
    competitor_name = models.CharField(max_length=255, blank=True)
    price_gap_notes = models.TextField(blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Loss reason for opportunity #{self.opportunity_id}"
