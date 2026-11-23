import hashlib
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization


class DmsEnterpriseTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme-dms",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("dms-owner", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        self.other = User.objects.create_user("dms-admin", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.other, organization=self.org, role=UserProfile.RoleCode.ADMIN
        )
        ensure_default_roles(self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_type_tag_metadata_comment_and_duplicate_file(self):
        kind = self.client.post(
            "/api/dms/types/",
            {"name": "Policy", "description": "Controlled document"},
            format="json",
        )
        self.assertEqual(kind.status_code, 201, kind.content)
        tag = self.client.post("/api/dms/tags/", {"name": "HR", "color": "#1B6A94"}, format="json")
        self.assertEqual(tag.status_code, 201, tag.content)
        meta = self.client.post(
            "/api/dms/metadata-types/",
            {"name": "author", "label": "Author"},
            format="json",
        )
        self.assertEqual(meta.status_code, 201, meta.content)

        payload = SimpleUploadedFile("policy.txt", b"hello dms", content_type="text/plain")
        created = self.client.post(
            "/api/dms/documents/",
            {"title": "Leave policy", "document_type": kind.data["id"], "file": payload},
            format="multipart",
        )
        self.assertEqual(created.status_code, 201, created.content)
        doc_id = created.data["id"]
        self.assertEqual(created.data["original_filename"], "policy.txt")
        self.assertEqual(created.data["checksum"], hashlib.sha256(b"hello dms").hexdigest())
        self.assertEqual(created.data["version"], 1)
        self.assertEqual(len(created.data["versions"]), 1)

        tagged = self.client.post(
            f"/api/dms/documents/{doc_id}/tags/",
            {"tag_ids": [tag.data["id"]]},
            format="json",
        )
        self.assertEqual(tagged.status_code, 200, tagged.content)
        self.assertEqual(tagged.data["tag_names"], "HR")

        noted = self.client.post(
            f"/api/dms/documents/{doc_id}/metadata/",
            {"metadata_type": meta.data["id"], "value": "Aisha"},
            format="json",
        )
        self.assertEqual(noted.status_code, 200, noted.content)
        self.assertEqual(noted.data["metadata_values"][0]["value"], "Aisha")

        comment = self.client.post(
            f"/api/dms/documents/{doc_id}/comment/",
            {"body": "Ready for review"},
            format="json",
        )
        self.assertEqual(comment.status_code, 200, comment.content)
        self.assertEqual(comment.data["comments"][0]["body"], "Ready for review")

        again = SimpleUploadedFile("copy.txt", b"hello dms", content_type="text/plain")
        twin = self.client.post(
            "/api/dms/documents/",
            {"title": "Copy of policy", "file": again},
            format="multipart",
        )
        self.assertEqual(twin.status_code, 201, twin.content)
        dups = self.client.get(f"/api/dms/documents/{doc_id}/duplicates/")
        self.assertEqual(dups.status_code, 200, dups.content)
        self.assertEqual(dups.data[0]["id"], twin.data["id"])

        same = self.client.post(
            f"/api/dms/documents/{doc_id}/link/",
            {"target": doc_id},
            format="json",
        )
        self.assertEqual(same.status_code, 400, same.content)
        linked = self.client.post(
            f"/api/dms/documents/{doc_id}/link/",
            {"target": twin.data["id"], "label": "Copy"},
            format="json",
        )
        self.assertEqual(linked.status_code, 200, linked.content)
        self.assertEqual(linked.data["links"][0]["target_title"], "Copy of policy")

    def test_checkout_blocks_other_user_and_review_flow(self):
        created = self.client.post("/api/dms/documents/", {"title": "Contract"}, format="json")
        self.assertEqual(created.status_code, 201, created.content)
        doc_id = created.data["id"]

        out = self.client.post(f"/api/dms/documents/{doc_id}/checkout/")
        self.assertEqual(out.status_code, 200, out.content)
        self.assertEqual(out.data["checked_out_by_name"], "dms-owner")

        other = APIClient()
        other.force_authenticate(self.other)
        blocked = other.post(
            f"/api/dms/documents/{doc_id}/new-version/",
            {"file": SimpleUploadedFile("v2.txt", b"next", content_type="text/plain")},
            format="multipart",
        )
        self.assertEqual(blocked.status_code, 400, blocked.content)

        submitted = self.client.post(f"/api/dms/documents/{doc_id}/submit/")
        self.assertEqual(submitted.status_code, 200, submitted.content)
        self.assertEqual(submitted.data["status"], "in_review")
        published = self.client.post(f"/api/dms/documents/{doc_id}/publish/")
        self.assertEqual(published.status_code, 200, published.content)
        self.assertEqual(published.data["status"], "published")
        archived = self.client.post(f"/api/dms/documents/{doc_id}/archive/")
        self.assertEqual(archived.status_code, 200, archived.content)
        restored = self.client.post(f"/api/dms/documents/{doc_id}/restore/")
        self.assertEqual(restored.status_code, 200, restored.content)
        self.assertEqual(restored.data["status"], "draft")

    def test_restricted_document_is_hidden_until_granted(self):
        created = self.client.post(
            "/api/dms/documents/",
            {"title": "Secret", "restricted": True},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        other = APIClient()
        other.force_authenticate(self.other)
        listing = other.get("/api/dms/documents/")
        self.assertEqual(listing.status_code, 200, listing.content)
        ids = [row["id"] for row in listing.data["results"]]
        self.assertNotIn(created.data["id"], ids)

        granted = self.client.post(
            f"/api/dms/documents/{created.data['id']}/grant-access/",
            {"user": self.other.id, "can_change": True},
            format="json",
        )
        self.assertEqual(granted.status_code, 200, granted.content)
        listing = other.get("/api/dms/documents/")
        ids = [row["id"] for row in listing.data["results"]]
        self.assertIn(created.data["id"], ids)

    def test_office365_file_is_saved_into_documents(self):
        from unittest.mock import patch

        from integrations.models import IntegrationConnection

        missing = self.client.get("/api/dms/documents/office365-files/")
        self.assertEqual(missing.status_code, 400, missing.content)

        IntegrationConnection.objects.create(
            organization=self.org,
            connector_key="excel_onedrive",
            is_enabled=True,
            status=IntegrationConnection.Status.ACTIVE,
            config={
                "tenant_id": "tenant",
                "client_id": "client",
                "mailbox_upn": "files@example.com",
                "drive_path": "SIERP",
            },
            secrets={"client_secret": "secret"},
            created_by=self.user,
        )
        payload = (
            b"hello dms",
            "Leave policy.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "https://example.com/policy",
        )
        with patch("integrations.office_files.acquire_app_token", return_value="token"), patch(
            "integrations.office_files.download_drive_item", return_value=payload
        ), patch(
            "integrations.office_files.list_drive_items",
            return_value=[{"id": "item-1", "name": "Leave policy.docx", "size": 9, "web_url": "", "mime_type": ""}],
        ):
            listed = self.client.get("/api/dms/documents/office365-files/")
            self.assertEqual(listed.status_code, 200, listed.content)
            self.assertEqual(listed.data[0]["name"], "Leave policy.docx")
            saved = self.client.post(
                "/api/dms/documents/from-office365/",
                {"item_id": "item-1"},
                format="json",
            )
            self.assertEqual(saved.status_code, 200, saved.content)
            self.assertEqual(saved.data["source"], "office365")
            self.assertEqual(saved.data["title"], "Leave policy")
            self.assertEqual(saved.data["checksum"], hashlib.sha256(b"hello dms").hexdigest())
            again = self.client.post(
                "/api/dms/documents/from-office365/",
                {"item_id": "item-1"},
                format="json",
            )
            self.assertEqual(again.status_code, 200, again.content)
            self.assertEqual(again.data["id"], saved.data["id"])
            self.assertEqual(again.data["version"], 2)

        with patch("integrations.office_files.acquire_app_token", return_value="token"), patch(
            "integrations.office_files.upload_drive_item",
            return_value={"id": "stored-9", "name": "Leave policy.docx", "web_url": "https://example.com/stored"},
        ):
            pushed = self.client.post(f"/api/dms/documents/{saved.data['id']}/save-to-office365/")
            self.assertEqual(pushed.status_code, 200, pushed.content)
            self.assertEqual(pushed.data["external_item_id"], "stored-9")
            self.assertEqual(pushed.data["external_web_url"], "https://example.com/stored")
