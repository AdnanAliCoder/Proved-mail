import tempfile
from pathlib import Path
from django.test import SimpleTestCase
from .services import detect_email_field, read_lead_file

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
