from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.import_engine import (
    build_all_templates_zip,
    build_template_csv,
    list_catalog,
    run_import,
)
import zipfile
import io
from core.models import Organization
from ops.models import Customer


class ImportHubTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Import Co",
            code="imp",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("importer", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save(update_fields=["owner"])
        ensure_default_roles(self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_catalog_and_template(self):
        self.assertGreaterEqual(len(list_catalog()), 10)
        csv = build_template_csv("customers")
        self.assertTrue(csv.startswith("code,"))

    def test_customer_upsert(self):
        text = "code,name,email\nC-IMP,Import Customer,a@b.com\n"
        dry = run_import(self.org, "customers", text, dry_run=True)
        self.assertEqual(dry["error_count"], 0)
        self.assertEqual(dry["row_count"], 1)
        live = run_import(self.org, "customers", text, dry_run=False)
        self.assertEqual(live["created"], 1)
        self.assertTrue(
            Customer.objects.filter(organization=self.org, code="C-IMP").exists()
        )
        live2 = run_import(self.org, "customers", text, dry_run=False)
        self.assertEqual(live2["updated"], 1)

    def test_api_catalog(self):
        res = self.client.get("/api/settings/import-hub/catalog/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.data.get("entities"))

    def test_api_template(self):
        res = self.client.get("/api/settings/import-hub/templates/employees/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn(b"employee_code", res.content)

    def test_templates_pack_zip(self):
        raw = build_all_templates_zip()
        self.assertGreater(len(raw), 100)
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            names = zf.namelist()
            self.assertIn("00_README.txt", names)
            self.assertIn("manifest.csv", names)
            self.assertTrue(any(n.endswith("_customers.csv") for n in names))
        res = self.client.get("/api/settings/import-hub/templates-pack/")
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res["Content-Type"], "application/zip")

    def test_zip_pack_import(self):
        from core.import_engine import run_import_zip

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "08_customers.csv",
                "code,name,email\nZ-IMP,Zip Customer,z@test.com\n",
            )
            zf.writestr(
                "07_vendors.csv",
                "code,name\nVZ-1,Zip Vendor\n",
            )
        dry = run_import_zip(self.org, buf.getvalue(), dry_run=True)
        self.assertEqual(dry["mode"], "zip_pack")
        self.assertEqual(dry["error_count"], 0)
        self.assertEqual(dry["file_count"], 2)
        live = run_import_zip(self.org, buf.getvalue(), dry_run=False)
        self.assertGreaterEqual(live["created"], 2)
        self.assertTrue(
            Customer.objects.filter(organization=self.org, code="Z-IMP").exists()
        )
        # API
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile(
            "pack.zip", buf.getvalue(), content_type="application/zip"
        )
        res = self.client.post(
            "/api/settings/import-hub/preview-pack/",
            {"file": upload},
            format="multipart",
        )
        self.assertEqual(res.status_code, 200, res.content)
