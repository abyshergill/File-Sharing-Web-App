from django.test import TestCase
from django.urls import reverse

from .models import User


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("boss", password="pw-Strong-123", role=User.Role.ADMIN)
        self.general = User.objects.create_user("joe", password="pw-Strong-123")

    def create(self, username, role):
        return self.client.post(reverse("accounts:user_create"), {
            "username": username, "email": "", "first_name": "", "last_name": "", "role": role,
            "password1": "Very-Strong-pw-42", "password2": "Very-Strong-pw-42",
        })

    def test_superuser_is_admin(self):
        su = User.objects.create_superuser("root", password="x")
        self.assertEqual(su.role, User.Role.ADMIN)
        self.assertTrue(su.is_app_admin)

    def test_admin_creates_admin_and_general(self):
        self.client.force_login(self.admin)
        self.create("newadmin", "admin")
        self.create("newuser", "general")
        self.assertEqual(User.objects.get(username="newadmin").role, User.Role.ADMIN)
        self.assertTrue(User.objects.get(username="newadmin").is_staff)
        new_user = User.objects.get(username="newuser")
        self.assertEqual(new_user.role, User.Role.GENERAL)
        self.assertEqual(new_user.created_by, self.admin)
        self.assertTrue(self.client.login(username="newuser", password="Very-Strong-pw-42"))

    def test_general_user_cannot_create_users(self):
        self.client.force_login(self.general)
        self.assertEqual(self.create("sneaky", "admin").status_code, 403)
        self.assertFalse(User.objects.filter(username="sneaky").exists())

    def test_admin_cannot_demote_or_delete_self(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_edit", args=[self.admin.pk]),
                         {"email": "", "first_name": "", "last_name": "", "role": "general", "is_active": "on"})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)
        self.client.post(reverse("accounts:user_delete", args=[self.admin.pk]))
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_deactivated_user_cannot_login(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_edit", args=[self.general.pk]),
                         {"email": "", "first_name": "", "last_name": "", "role": "general"})
        self.client.logout()
        self.assertFalse(self.client.login(username="joe", password="pw-Strong-123"))

    def test_delete_user_keeps_files(self):
        from sharing.models import SharedFile
        SharedFile.objects.create(original_name="x.txt", file="x.txt", uploaded_by=self.general)
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_delete", args=[self.general.pk]))
        self.assertEqual(SharedFile.objects.get().uploader_display, "N/A")
