from rest_framework import serializers

from .models import AppUser


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
        trim_whitespace=False,
    )


class AppUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppUser
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "role",
            "is_active",
            "is_staff",
        )
        read_only_fields = fields
