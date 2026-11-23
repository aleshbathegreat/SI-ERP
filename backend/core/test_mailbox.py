from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import Role, UserProfile, UserRole
from accounts.rbac import ensure_default_roles
from core.models import MailMessage, Organization, TenantEmailProfile, TenantSmtpSettings
from crm.models import Activity, Lead
from hr.models import Employee


class MailboxTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme-mail",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            "mail-owner", password="x-long-password-1", email="owner@acme.test"
        )
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        ensure_default_roles(self.org)
        self.clerk = User.objects.create_user(
            "mail-clerk", password="x-long-password-1", email="clerk@acme.test"
        )
        UserProfile.objects.create(
            user=self.clerk, organization=self.org, role=UserProfile.RoleCode.EMPLOYEE
        )
        role = Role.objects.create(
            organization=self.org,
            name="Clerk",
            code="mail-clerk",
            permissions={"dashboard": ["view"]},
        )
        UserRole.objects.create(user=self.clerk, role=role)
        self.employee = Employee.objects.create(
            organization=self.org,
            employee_code="E-1",
            first_name="Noor",
            last_name="Khan",
            email="noor@acme.test",
            created_by=self.user,
        )
        TenantSmtpSettings.objects.create(
            organization=self.org,
            host="smtp.acme.test",
            port=587,
            from_email="sales@acme.test",
            is_active=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_profile_requires_the_matching_owner(self):
        missing = self.client.post(
            "/api/settings/email-profiles/",
            {"name": "Noor", "email": "noor@acme.test", "owner_type": "employee"},
            format="json",
        )
        self.assertEqual(missing.status_code, 400, missing.content)

        created = self.client.post(
            "/api/settings/email-profiles/",
            {
                "name": "Noor Khan",
                "email": "noor@acme.test",
                "owner_type": "employee",
                "employee": self.employee.id,
                "purpose": "crm",
                "inbound": "imap",
                "imap_host": "imap.acme.test",
                "imap_password": "secret-pass",
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.data["owner_label"], "Noor Khan")
        self.assertNotIn("imap_password", created.data)
        self.assertTrue(created.data["imap_password_set"])
        self.assertEqual(
            TenantEmailProfile.objects.get(pk=created.data["id"]).imap_password,
            "secret-pass",
        )

    @patch("core.mailbox._smtp_send")
    def test_send_tracks_the_message_and_crm_activity(self, smtp):
        profile = TenantEmailProfile.objects.create(
            organization=self.org,
            name="Sales",
            email="sales@acme.test",
            owner_type="shared",
            purpose="crm",
            signature="Acme sales",
            created_by=self.user,
        )
        lead = Lead.objects.create(
            organization=self.org, name="Sara", email="sara@buyer.test", created_by=self.user
        )
        sent = self.client.post(
            "/api/settings/mail-messages/send/",
            {
                "profile": profile.id,
                "to": "sara@buyer.test",
                "subject": "Proposal",
                "body": "Please find the proposal.",
                "lead": lead.id,
            },
            format="json",
        )
        self.assertEqual(sent.status_code, 201, sent.content)
        self.assertEqual(sent.data["status"], "sent")
        self.assertIn("Acme sales", sent.data["body"])
        smtp.assert_called_once()
        self.assertEqual(MailMessage.objects.filter(profile=profile, status="sent").count(), 1)
        self.assertTrue(
            Activity.objects.filter(lead=lead, type="email", outcome="Sent").exists()
        )

    @patch("core.mailbox._smtp_send")
    def test_a_user_cannot_send_as_someone_elses_mailbox(self, smtp):
        personal = TenantEmailProfile.objects.create(
            organization=self.org,
            name="Owner",
            email="owner@acme.test",
            owner_type="user",
            user=self.user,
            created_by=self.user,
        )
        self.client.force_authenticate(self.clerk)
        denied = self.client.post(
            "/api/settings/mail-messages/send/",
            {"profile": personal.id, "to": "sara@buyer.test", "subject": "Hi", "body": "Hi"},
            format="json",
        )
        self.assertEqual(denied.status_code, 400, denied.content)
        smtp.assert_not_called()
        self.assertFalse(MailMessage.objects.filter(profile=personal).exists())

    @patch("core.email_views.pull_inbox")
    def test_inbox_copies_mail_once_and_links_the_lead(self, pull):
        profile = TenantEmailProfile.objects.create(
            organization=self.org,
            name="Sales",
            email="sales@acme.test",
            inbound="imap",
            imap_host="imap.acme.test",
            created_by=self.user,
        )
        Lead.objects.create(
            organization=self.org, name="Sara", email="sara@buyer.test", created_by=self.user
        )
        pull.return_value = [
            {
                "message_id": "<abc@buyer.test>",
                "subject": "Re: Proposal",
                "body": "Thanks",
                "from_email": "Sara@buyer.test",
                "to_emails": "sales@acme.test",
                "occurred_at": "2026-11-03T10:00:00+05:00",
            }
        ]
        first = self.client.post(
            "/api/settings/mail-messages/fetch/",
            {"profile": profile.id},
            format="json",
        )
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(first.data["imported"], 1)
        second = self.client.post(
            "/api/settings/mail-messages/fetch/",
            {"profile": profile.id},
            format="json",
        )
        self.assertEqual(second.data["imported"], 0)
        self.assertEqual(second.data["skipped"], 1)
        row = MailMessage.objects.get(message_id="<abc@buyer.test>")
        self.assertEqual(row.direction, "in")
        self.assertEqual(row.lead.email, "sara@buyer.test")
        self.assertTrue(Activity.objects.filter(lead=row.lead, outcome="Received").exists())
