from django.contrib.auth.models import AbstractUser
from django.db import models


class AppUser(AbstractUser):
    """
    Custom user model for FOXD Tender Pipeline.

    Adds a role (for RBAC), an optional display name, and standard
    created/updated timestamps. Internal users only — no self-signup.
    """

    class Role(models.TextChoices):
        DIRECTOR = "director", "Director"
        ESTIMATOR = "estimator", "Estimator"
        PROJECT_MANAGER = "project_manager", "Project Manager"
        ADMIN = "admin", "Admin"
        READ_ONLY = "read_only", "Read Only"

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.READ_ONLY,
    )
    display_name = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return self.display_name or self.username
