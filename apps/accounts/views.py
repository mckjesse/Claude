from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .filters import BuilderFilter, ContactFilter
from .models import Builder, Contact
from .serializers import BuilderSerializer, ContactSerializer


class BuilderViewSet(viewsets.ModelViewSet):
    queryset = Builder.objects.all()
    serializer_class = BuilderSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = BuilderFilter
    search_fields = ["name", "notes"]
    ordering_fields = [
        "name",
        "tier",
        "revenue_last_12_months",
        "last_contact_date",
        "next_contact_date",
        "created_at",
    ]
    ordering = ["name"]

    def get_queryset(self):
        return Builder.objects.select_related("account_owner")


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ContactFilter
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "role",
        "builder__name",
    ]
    ordering_fields = [
        "last_name",
        "first_name",
        "relationship_strength",
        "last_contact_date",
        "created_at",
    ]
    ordering = ["last_name", "first_name"]

    def get_queryset(self):
        return Contact.objects.select_related(
            "builder", "moved_from_builder"
        )
