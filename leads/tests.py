import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from django.test import SimpleTestCase
from .services import detect_email_field, read_lead_file
from .views import _spreadsheet_safe_value
from .models import EmailJob, SitePage, SiteSettings, VerificationRow

class LeadFileParsingTests(SimpleTestCase):
    def test_email_header_detection(self):
        self.assertEqual(detect_email_field(["Name", "Work Email", "Company"]), "Work Email")

    def test_csv_keeps_original_columns(self):
        content = "Name,Email,Company\nAsha,asha@example.com,Example Inc\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.csv"
            path.write_text(content, encoding="utf-8")
            headers, rows, email_field = read_lead_file(str(path), "sample.csv")
        self.assertEqual(headers, ["Name", "Email", "Company"])
        self.assertEqual(email_field, "Email")
        self.assertEqual(rows[0]["Name"], "Asha")
        self.assertEqual(rows[0]["Company"], "Example Inc")

    def test_missing_email_header_is_detected(self):
        self.assertIsNone(detect_email_field(["Name", "Company", "Title"]))


from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    PROVEDMAILS_ADMIN_EMAIL="adnan@example.com",
    PROVEDMAILS_ADMIN_SIGNUP_KEY="test-only-bootstrap-key",
)
class AdminBootstrapTests(TestCase):
    def test_only_one_admin_can_be_created_and_password_is_hashed(self):
        password = "T3st!MoreSecurePassphrase94"
        response = self.client.post(
            reverse("bootstrap_admin"),
            {
                "full_name": "Adnan Ali",
                "email": "adnan@example.com",
                "setup_key": "test-only-bootstrap-key",
                "password1": password,
                "password2": password,
            },
        )
        self.assertRedirects(response, reverse("control_dashboard"))
        user = get_user_model().objects.get(email="adnan@example.com")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(password))
        self.assertNotEqual(user.password, password)

        second_attempt = self.client.get(reverse("bootstrap_admin"))
        self.assertRedirects(second_attempt, reverse("login"))
        self.assertEqual(get_user_model().objects.filter(is_superuser=True).count(), 1)

    def test_wrong_setup_key_does_not_create_user(self):
        response = self.client.post(
            reverse("bootstrap_admin"),
            {
                "full_name": "Adnan Ali",
                "email": "adnan@example.com",
                "setup_key": "wrong-key",
                "password1": "T3st!MoreSecurePassphrase94",
                "password2": "T3st!MoreSecurePassphrase94",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.filter(is_superuser=True).exists())



class SpreadsheetSafetyTests(SimpleTestCase):
    def test_formula_like_cells_are_neutralized(self):
        cases = [
            ("=1+1", "'=1+1"),
            ("  =HYPERLINK(\"https://example.com\")", "'  =HYPERLINK(\"https://example.com\")"),
            ("+SUM(A1:A2)", "'+SUM(A1:A2)"),
            ("-2+3", "'-2+3"),
            ("@SUM(A1:A2)", "'@SUM(A1:A2)"),
            ("\t=1+1", "'\t=1+1"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(_spreadsheet_safe_value(value), expected)

    def test_safe_values_remain_unchanged(self):
        self.assertEqual(_spreadsheet_safe_value("person@example.com"), "person@example.com")
        self.assertEqual(_spreadsheet_safe_value(42), 42)
        self.assertEqual(_spreadsheet_safe_value(None), "")


class SpreadsheetExportEndpointTests(TestCase):
    def test_csv_export_neutralizes_formula_like_lead_values(self):
        user = get_user_model().objects.create_superuser(
            username="owner@example.com",
            email="owner@example.com",
            password="T3st!MoreSecurePassphrase94",
        )
        job = EmailJob.objects.create(
            owner=user,
            source_file="",
            source_filename="sample.csv",
            status=EmailJob.Status.COMPLETED,
            total=1,
            completed=1,
        )
        VerificationRow.objects.create(
            job=job,
            position=1,
            source_row={"Name": "=HYPERLINK(\"https://example.com\",\"open\")", "Email": "person@example.com"},
            verified_email="person@example.com",
            status="valid",
            reason="smtp_ok",
            confidence=100,
        )
        self.client.force_login(user)
        response = self.client.get(
            reverse("download_results", kwargs={"job_id": job.pk}),
            {"type": "all", "format": "csv"},
        )
        self.assertEqual(response.status_code, 200)
        content = b"".join(response.streaming_content).decode("utf-8-sig")
        self.assertIn("'=HYPERLINK", content)


class PublicBrandingAndSeoTests(TestCase):
    def test_site_name_setting_updates_global_brand(self):
        site_settings = SiteSettings.objects.get(pk=1)
        site_settings.site_name = "MailProof Studio"
        site_settings.save()
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'content="MailProof Studio"', html=False)
        self.assertContains(response, "<strong>MailProof Studio</strong>", html=False)

    def test_sitemap_is_valid_xml_and_excludes_unpublished_pages(self):
        SitePage.objects.create(
            slug="published-guide",
            title="Published guide",
            seo_title="Published guide",
            meta_description="A public guide.",
            body_text="Guide",
            is_published=True,
        )
        SitePage.objects.create(
            slug="draft-guide",
            title="Draft guide",
            seo_title="Draft guide",
            meta_description="A draft.",
            body_text="Draft",
            is_published=False,
        )
        response = self.client.get(reverse("sitemap_xml"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("application/xml"))
        root = ET.fromstring(response.content)
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [node.text for node in root.findall("sm:url/sm:loc", namespace)]
        self.assertTrue(any("/pages/published-guide/" in location for location in locations))
        self.assertFalse(any("/pages/draft-guide/" in location for location in locations))
        self.assertTrue(root.findall("sm:url/sm:lastmod", namespace))
