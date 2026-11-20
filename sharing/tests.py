import io
import shutil
import tempfile
from datetime import timedelta

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import ActivityLog, SharedFile, SiteSettings

TEMP_MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA, FILESHARE_MAX_FAILED_ATTEMPTS=3, FILESHARE_PAGE_SIZE=5)
class BaseTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_user("boss", password="pw-Strong-123", role=User.Role.ADMIN)
        self.general = User.objects.create_user("joe", password="pw-Strong-123")

    def set_access(self, upload=False, download=False):
        site = SiteSettings.load()
        site.public_upload, site.public_download = upload, download
        site.save()

    def upload(self, name="hello.txt", content=b"hello", ip="10.0.0.5"):
        f = SimpleUploadedFile(name, content, content_type="text/plain")
        return self.client.post(reverse("sharing:upload"), {"files": [f]}, REMOTE_ADDR=ip)


class AccessModeTests(BaseTest):
    def test_anonymous_cannot_upload_when_restricted(self):
        resp = self.upload()
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp.url)
        self.assertEqual(SharedFile.objects.count(), 0)

    def test_general_user_can_upload_when_restricted(self):
        self.client.force_login(self.general)
        resp = self.upload()
        self.assertRedirects(resp, reverse("sharing:upload_done"))
        f = SharedFile.objects.get()
        self.assertEqual(f.uploaded_by, self.general)
        self.assertEqual(f.uploader_ip, "10.0.0.5")

    def test_public_upload_logs_na_and_ip(self):
        self.set_access(upload=True)
        self.upload(ip="203.0.113.9")
        log = ActivityLog.objects.get(action=ActivityLog.Action.UPLOAD)
        self.assertEqual(log.username, "N/A")
        self.assertIsNone(log.user)
        self.assertEqual(log.ip_address, "203.0.113.9")
        self.assertEqual(log.file_name, "hello.txt")
        self.assertEqual(SharedFile.objects.get().uploader_display, "N/A")

    def test_anonymous_download_blocked_when_restricted(self):
        self.client.force_login(self.general)
        self.upload()
        self.client.logout()
        code = SharedFile.objects.get().share_code
        resp = self.client.get(reverse("sharing:download", args=[code]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), resp.url)

    def test_public_download_logs_na_and_ip(self):
        self.set_access(upload=True, download=True)
        self.upload(content=b"payload")
        code = SharedFile.objects.get().share_code
        resp = self.client.get(reverse("sharing:download", args=[code]), REMOTE_ADDR="198.51.100.7")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), b"payload")
        self.assertIn("attachment", resp["Content-Disposition"])
        log = ActivityLog.objects.get(action=ActivityLog.Action.DOWNLOAD)
        self.assertEqual((log.username, log.ip_address), ("N/A", "198.51.100.7"))
        self.assertEqual(SharedFile.objects.get().download_count, 1)

    def test_logged_in_download_records_username(self):
        self.client.force_login(self.general)
        self.upload()
        code = SharedFile.objects.get().share_code
        self.client.get(reverse("sharing:download", args=[code]))
        self.assertEqual(ActivityLog.objects.get(action="download").username, "joe")


class ShareCodeTests(BaseTest):
    def test_codes_are_unique_and_long(self):
        self.client.force_login(self.general)
        self.upload("a.txt")
        self.upload("b.txt")
        codes = list(SharedFile.objects.values_list("share_code", flat=True))
        self.assertEqual(len(set(codes)), 2)
        self.assertTrue(all(len(c) >= 20 for c in codes))

    def test_find_accepts_full_link(self):
        self.client.force_login(self.general)
        self.upload()
        code = SharedFile.objects.get().share_code
        resp = self.client.post(reverse("sharing:find"), {"code": f"http://testserver/f/{code}/"})
        self.assertRedirects(resp, reverse("sharing:file_detail", args=[code]))

    def test_lockout_after_failed_codes(self):
        self.set_access(download=True)
        url = reverse("sharing:file_detail", args=["nope"])
        for _ in range(3):
            self.client.get(url)
        self.assertEqual(ActivityLog.objects.filter(action="failed_lookup").count(), 3)
        # Even a valid code is refused while locked out.
        self.set_access(upload=True, download=True)
        self.upload()
        code = SharedFile.objects.get().share_code
        resp = self.client.get(reverse("sharing:download", args=[code]))
        self.assertRedirects(resp, reverse("sharing:find"))
        # A different IP is unaffected.
        resp = self.client.get(reverse("sharing:download", args=[code]), REMOTE_ADDR="10.9.9.9")
        self.assertEqual(resp.status_code, 200)

    def test_stored_name_is_random(self):
        self.client.force_login(self.general)
        self.upload("../../etc/passwd.txt")
        f = SharedFile.objects.get()
        self.assertNotIn("..", f.file.name)
        self.assertNotIn("passwd", f.file.name)


class FileManagementTests(BaseTest):
    def test_owner_and_admin_can_delete_others_cannot(self):
        self.client.force_login(self.admin)
        self.upload()
        f = SharedFile.objects.get()
        self.client.force_login(self.general)
        resp = self.client.post(reverse("sharing:delete_file", args=[f.pk]))
        self.assertEqual(resp.status_code, 404)
        self.client.force_login(self.admin)
        self.client.post(reverse("sharing:delete_file", args=[f.pk]))
        self.assertFalse(SharedFile.objects.exists())
        self.assertTrue(ActivityLog.objects.filter(action="delete", file_name="hello.txt").exists())

    def test_my_files_pagination(self):
        self.client.force_login(self.general)
        for i in range(7):
            self.upload(f"f{i}.txt")
        resp = self.client.get(reverse("sharing:my_files"))
        self.assertEqual(len(resp.context["page"].object_list), 5)
        resp = self.client.get(reverse("sharing:my_files") + "?page=2")
        self.assertEqual(len(resp.context["page"].object_list), 2)


class PanelTests(BaseTest):
    def test_panel_admin_only(self):
        for name in ["dashboard", "files", "logs", "settings", "cleanup"]:
            url = reverse(f"panel:{name}")
            self.client.force_login(self.general)
            self.assertEqual(self.client.get(url).status_code, 403, name)
            self.client.force_login(self.admin)
            self.assertEqual(self.client.get(url).status_code, 200, name)

    def test_admin_changes_access_mode(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("panel:settings"), {"public_upload": "on", "public_download": "on"})
        site = SiteSettings.load()
        self.assertTrue(site.public_upload and site.public_download)
        self.assertTrue(ActivityLog.objects.filter(action="settings").exists())

    def test_logs_filter_and_pagination_keep_query(self):
        self.client.force_login(self.general)
        for i in range(6):
            self.upload(f"f{i}.txt")
        self.client.force_login(self.admin)
        resp = self.client.get(reverse("panel:logs"), {"action": "upload"})
        self.assertEqual(resp.context["page"].paginator.count, 6)
        self.assertContains(resp, "?action=upload&page=2")

    def test_cleanup_deletes_only_old_files(self):
        self.client.force_login(self.general)
        self.upload("old.txt")
        self.upload("new.txt")
        old = SharedFile.objects.get(original_name="old.txt")
        SharedFile.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=40))
        path = old.file.path

        self.client.force_login(self.admin)
        resp = self.client.get(reverse("panel:cleanup"), {"days": 30})
        self.assertEqual(resp.context["preview"]["count"], 1)
        self.client.post(reverse("panel:cleanup"), {"days": 30, "confirm": "yes"})
        self.assertEqual(list(SharedFile.objects.values_list("original_name", flat=True)), ["new.txt"])
        import os
        self.assertFalse(os.path.exists(path))
        self.assertTrue(ActivityLog.objects.filter(action="cleanup").exists())
        # Upload log for the deleted file is preserved.
        self.assertTrue(ActivityLog.objects.filter(action="upload", file_name="old.txt").exists())

    def test_cleanup_command(self):
        self.client.force_login(self.general)
        self.upload("old.txt")
        SharedFile.objects.update(created_at=timezone.now() - timedelta(days=100))
        call_command("cleanup_old_files", days=90, stdout=io.StringIO())
        self.assertFalse(SharedFile.objects.exists())
