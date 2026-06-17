import django_filters

from .models import Builder, Contact


class BuilderFilter(django_filters.FilterSet):
    class Meta:
        model = Builder
        fields = ["tier", "margin_quality", "account_owner"]


class ContactFilter(django_filters.FilterSet):
    # Accept both ``builder`` and ``builder_id``.
    builder_id = django_filters.NumberFilter(field_name="builder_id")

    class Meta:
        model = Contact
        fields = [
            "builder",
            "builder_id",
            "relationship_strength",
        ]
