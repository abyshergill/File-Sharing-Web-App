from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class AppUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        # Anyone created with `createsuperuser` is an application admin.
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Application user. Every account is either an Admin or a General user."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        GENERAL = "general", "General user"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.GENERAL)
    created_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_users",
    )

    objects = AppUserManager()

    @property
    def is_app_admin(self):
        return self.is_active and (self.role == self.Role.ADMIN or self.is_superuser)

    def save(self, *args, **kwargs):
        # Admins can open the built-in Django admin too.
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        elif not self.is_superuser:
            self.is_staff = False
        super().save(*args, **kwargs)
