import re
from django import forms
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from .models import SiteSettings, SitePage

class AdminBootstrapForm(forms.Form):
    full_name = forms.CharField(max_length=150, label="Your name", initial="Adnan Ali")
    email = forms.EmailField()
    setup_key = forms.CharField(label="One-time setup key", widget=forms.PasswordInput)
    password1 = forms.CharField(label="Create a password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if not settings.PROVEDMAILS_ADMIN_EMAIL:
            raise forms.ValidationError("Admin bootstrap is not configured on the server.")
        if email != settings.PROVEDMAILS_ADMIN_EMAIL:
            raise forms.ValidationError("This email is not authorized for the one-time administrator account.")
        return email

    def clean_setup_key(self):
        import secrets
        value = self.cleaned_data["setup_key"]
        expected = settings.PROVEDMAILS_ADMIN_SIGNUP_KEY
        if not expected or not secrets.compare_digest(value, expected):
            raise forms.ValidationError("The one-time setup key is incorrect.")
        return value

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password1")
        confirm = cleaned.get("password2")
        if password and confirm and password != confirm:
            self.add_error("password2", "Passwords do not match.")
        if password:
            from django.contrib.auth import get_user_model
            fake_user = get_user_model()(email=cleaned.get("email", ""), username=cleaned.get("email", ""))
            try:
                validate_password(password, user=fake_user)
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["site_name", "tagline", "site_url", "homepage_title", "meta_description",
                  "adsense_code", "analytics_code", "extra_head_code"]
        widgets = {
            "adsense_code": forms.Textarea(attrs={"rows": 5, "spellcheck": "false"}),
            "analytics_code": forms.Textarea(attrs={"rows": 5, "spellcheck": "false"}),
            "extra_head_code": forms.Textarea(attrs={"rows": 5, "spellcheck": "false"}),
            "meta_description": forms.Textarea(attrs={"rows": 2}),
        }


class SearchConsoleFileForm(forms.Form):
    verification_file = forms.FileField(label="Google Search Console HTML verification file")

    def clean_verification_file(self):
        uploaded = self.cleaned_data["verification_file"]
        name = uploaded.name
        if not re.fullmatch(r"google[A-Za-z0-9_-]+\.html", name, flags=re.IGNORECASE):
            raise forms.ValidationError("Use the original Google file name, such as google123abc.html.")
        if uploaded.size > 25 * 1024:
            raise forms.ValidationError("Verification files must be 25 KB or smaller.")
        try:
            content = uploaded.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            raise forms.ValidationError("The verification file must be UTF-8 text.")
        if "google-site-verification:" not in content.lower():
            raise forms.ValidationError("This file does not look like a Google site verification file.")
        uploaded.seek(0)
        return uploaded


class SitePageForm(forms.ModelForm):
    class Meta:
        model = SitePage
        fields = ["title", "seo_title", "meta_description", "body_text", "is_published"]
        widgets = {
            "body_text": forms.Textarea(attrs={"rows": 14}),
            "meta_description": forms.Textarea(attrs={"rows": 2}),
        }
