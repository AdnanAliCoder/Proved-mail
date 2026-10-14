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
