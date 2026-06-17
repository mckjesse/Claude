from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Builder(TimestampedModel):
    class Tier(models.TextChoices):
        TIER_1 = "tier_1", "Tier 1"
        TIER_2 = "tier_2", "Tier 2"
        TIER_3 = "tier_3", "Tier 3"
        UNCLASSIFIED = "unclassified", "Unclassified"

    class MarginQuality(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        UNKNOWN = "unknown", "Unknown"

    name = models.CharField(max_length=255, unique=True)
    tier = models.CharField(
        max_length=20, choices=Tier.choices, default=Tier.UNCLASSIFIED
    )
    revenue_last_12_months = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    margin_quality = models.CharField(
        max_length=20,
        choices=MarginQuality.choices,
        default=MarginQuality.UNKNOWN,
    )
    account_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_builders",
    )
    last_contact_date = models.DateField(null=True, blank=True)
    next_contact_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Contact(TimestampedModel):
    class RelationshipStrength(models.TextChoices):
        STRONG = "strong", "Strong"
        MODERATE = "moderate", "Moderate"
        WEAK = "weak", "Weak"
        NEW = "new", "New"

    builder = models.ForeignKey(
        Builder, on_delete=models.CASCADE, related_name="contacts"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=150, blank=True)
    mobile = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    relationship_strength = models.CharField(
        max_length=20,
        choices=RelationshipStrength.choices,
        default=RelationshipStrength.NEW,
    )
    last_contact_date = models.DateField(null=True, blank=True)
    next_contact_date = models.DateField(null=True, blank=True)
    moved_from_builder = models.ForeignKey(
        Builder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts_moved_from",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()
