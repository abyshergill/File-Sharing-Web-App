from django import forms
from django.conf import settings
from django.template.defaultfilters import filesizeformat

from .models import ActivityLog, SiteSettings


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)] if data else []


MAX_FILES_PER_UPLOAD = 20


class UploadForm(forms.Form):
    files = MultipleFileField(
        label="Choose file(s)",
        widget=MultipleFileInput(attrs={"multiple": True}),
    )

    def clean_files(self):
        files = self.cleaned_data["files"]
        if not files:
            raise forms.ValidationError("Please choose at least one file.")
        if len(files) > MAX_FILES_PER_UPLOAD:
            raise forms.ValidationError(f"You can upload at most {MAX_FILES_PER_UPLOAD} files at once.")
        limit = settings.FILESHARE_MAX_UPLOAD_MB * 1024 * 1024
        for f in files:
            if f.size > limit:
                raise forms.ValidationError(
                    f"“{f.name}” is {filesizeformat(f.size)}; the limit is {settings.FILESHARE_MAX_UPLOAD_MB} MB."
                )
        return files


class ShareCodeForm(forms.Form):
    code = forms.CharField(
        label="Share code",
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Paste the share code or link", "autocomplete": "off"}),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        # Accept a full share link as well as the bare code.
        if "/f/" in code:
            code = code.split("/f/", 1)[1].split("/", 1)[0]
        return code[:64]


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["public_upload", "public_download"]
        labels = {
            "public_upload": "Anyone can upload (no login required)",
            "public_download": "Anyone with a share code can download (no login required)",
        }


class CleanupForm(forms.Form):
    days = forms.IntegerField(
        label="Delete files uploaded more than this many days ago",
        min_value=1,
        max_value=36500,
        initial=30,
    )


class FileSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Search",
                        widget=forms.TextInput(attrs={"placeholder": "File name, code, uploader or IP"}))


class LogFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Search",
                        widget=forms.TextInput(attrs={"placeholder": "File name, code, user or IP"}))
    action = forms.ChoiceField(required=False, choices=[("", "All actions")] + list(ActivityLog.Action.choices))
