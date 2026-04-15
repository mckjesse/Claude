"""
Promote Opportunity.project_code ("Project ID") to a required + unique
identifier.

Historically the column was `blank=True` with no uniqueness, so existing
rows can have empty strings or duplicates. We normalise those before
applying the new constraint so the migration is safe to run against any
real database.
"""
from django.db import migrations, models


def _ensure_unique_project_codes(apps, schema_editor):
    Opportunity = apps.get_model("pipeline", "Opportunity")
    used: set[str] = set()
    for opp in Opportunity.objects.order_by("id"):
        code = (opp.project_code or "").strip()
        if not code:
            code = f"AUTO-{opp.pk:05d}"
        if code in used:
            code = f"{code}-{opp.pk}"
        used.add(code)
        if code != opp.project_code:
            opp.project_code = code
            opp.save(update_fields=["project_code"])


class Migration(migrations.Migration):

    dependencies = [
        ("pipeline", "0003_alter_company_options_alter_opportunity_options"),
    ]

    operations = [
        migrations.RunPython(
            _ensure_unique_project_codes,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="opportunity",
            name="project_code",
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
