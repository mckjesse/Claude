"""
Seed sample Builder and Contact records for local development.

Usage:
    python manage.py seed_accounts
    python manage.py seed_accounts --reset
"""
from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Builder, Contact
from apps.users.models import AppUser

BUILDERS = [
    {
        "name": "Stirling Constructions Pty Ltd",
        "tier": Builder.Tier.TIER_1,
        "revenue_last_12_months": "2450000.00",
        "margin_quality": Builder.MarginQuality.HIGH,
    },
    {
        "name": "Kingsway Build Group",
        "tier": Builder.Tier.TIER_2,
        "revenue_last_12_months": "980000.00",
        "margin_quality": Builder.MarginQuality.LOW,
    },
    {
        "name": "Harbourline Construction",
        "tier": Builder.Tier.TIER_1,
        "revenue_last_12_months": "1870000.00",
        "margin_quality": Builder.MarginQuality.MEDIUM,
    },
    {
        "name": "Redfern Commercial Builders",
        "tier": Builder.Tier.TIER_2,
        "revenue_last_12_months": "720000.00",
        "margin_quality": Builder.MarginQuality.MEDIUM,
    },
    {
        "name": "Pacific Edge Constructions",
        "tier": Builder.Tier.TIER_3,
        "revenue_last_12_months": "340000.00",
        "margin_quality": Builder.MarginQuality.UNKNOWN,
    },
]

CONTACTS = [
    ("Jane", "Harper", "Senior Contracts Manager", "Stirling Constructions Pty Ltd", Contact.RelationshipStrength.STRONG),
    ("Tom", "Nguyen", "Tenders Coordinator", "Stirling Constructions Pty Ltd", Contact.RelationshipStrength.MODERATE),
    ("Amelia", "Walsh", "Procurement Lead", "Kingsway Build Group", Contact.RelationshipStrength.WEAK),
    ("Noah", "Carter", "Commercial Manager", "Harbourline Construction", Contact.RelationshipStrength.STRONG),
    ("Isla", "Robinson", "Estimator", "Harbourline Construction", Contact.RelationshipStrength.MODERATE),
    ("Oliver", "Schmidt", "Project Director", "Redfern Commercial Builders", Contact.RelationshipStrength.NEW),
    ("Grace", "McKenzie", "Head of Projects", "Pacific Edge Constructions", Contact.RelationshipStrength.NEW),
]


class Command(BaseCommand):
    help = "Seed sample Builder and Contact records for local dev."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing accounts data before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            Contact.objects.all().delete()
            Builder.objects.all().delete()
            self.stdout.write("Reset accounts data.")

        owner = (
            AppUser.objects.filter(role=AppUser.Role.DIRECTOR).first()
            or AppUser.objects.first()
        )
        today = date.today()

        with transaction.atomic():
            builders = {}
            for spec in BUILDERS:
                b, _ = Builder.objects.update_or_create(
                    name=spec["name"],
                    defaults={
                        **spec,
                        "account_owner": owner,
                        "last_contact_date": today - timedelta(days=14),
                        "next_contact_date": today + timedelta(days=14),
                    },
                )
                builders[spec["name"]] = b

            for first, last, role, builder_name, strength in CONTACTS:
                Contact.objects.update_or_create(
                    builder=builders[builder_name],
                    first_name=first,
                    last_name=last,
                    defaults={
                        "role": role,
                        "mobile": f"+61 4{hash(first) % 90 + 10} {hash(last) % 900 + 100} {hash(role) % 900 + 100}",
                        "email": f"{first.lower()}.{last.lower()}@{builder_name.split()[0].lower()}.com.au",
                        "relationship_strength": strength,
                        "last_contact_date": today - timedelta(days=7),
                        "next_contact_date": today + timedelta(days=21),
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {Builder.objects.count()} builders, "
                f"{Contact.objects.count()} contacts."
            )
        )
