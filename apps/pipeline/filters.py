import django_filters
from django.utils import timezone

from .models import FollowUpTask, Opportunity, Quote


class OpportunityFilter(django_filters.FilterSet):
    stage = django_filters.MultipleChoiceFilter(choices=Opportunity.Stage.choices)
    status = django_filters.MultipleChoiceFilter(choices=Opportunity.Status.choices)

    submission_due_from = django_filters.DateFilter(
        field_name="submission_due_date", lookup_expr="gte"
    )
    submission_due_to = django_filters.DateFilter(
        field_name="submission_due_date", lookup_expr="lte"
    )
    expected_award_from = django_filters.DateFilter(
        field_name="expected_award_date", lookup_expr="gte"
    )
    expected_award_to = django_filters.DateFilter(
        field_name="expected_award_date", lookup_expr="lte"
    )
    min_value = django_filters.NumberFilter(
        field_name="estimated_contract_value", lookup_expr="gte"
    )
    max_value = django_filters.NumberFilter(
        field_name="estimated_contract_value", lookup_expr="lte"
    )

    class Meta:
        model = Opportunity
        fields = [
            "project_code",   # Project ID — exact-match lookup
            "company",
            "estimator",
            "assigned_user",
            "sector",
            "tender_type",
            "opportunity_source",
        ]


class FollowUpTaskFilter(django_filters.FilterSet):
    due_from = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_to = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    is_overdue = django_filters.BooleanFilter(method="filter_is_overdue")

    class Meta:
        model = FollowUpTask
        fields = [
            "opportunity",
            "assigned_to_user",
            "related_quote",
            "task_type",
            "priority",
            "status",
        ]

    def filter_is_overdue(self, queryset, name, value):
        today = timezone.localdate()
        active = queryset.exclude(
            status__in=[
                FollowUpTask.Status.COMPLETED,
                FollowUpTask.Status.CANCELLED,
            ]
        )
        if value:
            return active.filter(due_date__lt=today)
        return active.filter(due_date__gte=today)


class QuoteFilter(django_filters.FilterSet):
    # Accept both ``opportunity`` and ``opportunity_id`` so the frontend
    # works regardless of which key it sends.
    opportunity_id = django_filters.NumberFilter(field_name="opportunity_id")

    class Meta:
        model = Quote
        fields = ["opportunity", "opportunity_id", "quote_status"]
