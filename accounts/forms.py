from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class AdminUserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email", "first_name", "last_name", "role"]


class AdminUserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "is_active"]
        labels = {"is_active": "Account active (can sign in)"}

    def __init__(self, *args, acting_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.acting_user = acting_user

    def clean(self):
        cleaned = super().clean()
        user = self.instance
        if self.acting_user and user.pk == self.acting_user.pk:
            if cleaned.get("role") != User.Role.ADMIN:
                self.add_error("role", "You cannot remove your own admin role.")
            if not cleaned.get("is_active"):
                self.add_error("is_active", "You cannot deactivate your own account.")
        demoting = cleaned.get("role") != User.Role.ADMIN or not cleaned.get("is_active")
        if user.role == User.Role.ADMIN and demoting and is_last_active_admin(user):
            raise forms.ValidationError("This is the last active admin; create another admin first.")
        return cleaned


def is_last_active_admin(user):
    return not User.objects.filter(role=User.Role.ADMIN, is_active=True).exclude(pk=user.pk).exists()
