from rest_framework import serializers

from apps.users.serializers import AppUserSerializer

from .models import Builder, Contact


class BuilderMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Builder
        fields = ("id", "name", "tier")
        read_only_fields = fields


class BuilderSerializer(serializers.ModelSerializer):
    account_owner_detail = AppUserSerializer(
        source="account_owner", read_only=True
    )

    class Meta:
        model = Builder
        fields = "__all__"


class ContactSerializer(serializers.ModelSerializer):
    builder_detail = BuilderMinimalSerializer(
        source="builder", read_only=True
    )
    moved_from_builder_detail = BuilderMinimalSerializer(
        source="moved_from_builder", read_only=True
    )

    class Meta:
        model = Contact
        fields = "__all__"
