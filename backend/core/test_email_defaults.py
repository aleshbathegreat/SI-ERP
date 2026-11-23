from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.email_defaults import DEFAULT_EMAIL_TEMPLATES, ensure_default_email_templates
from core.models import EmailTemplate, Organization


class DefaultEmailTemplateTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme-mail-tpl",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("tpl-owner", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        ensure_default_roles(self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_defaults_are_created_once_and_edits_stay(self):
        created = ensure_default_email_templates(self.org)
        self.assertEqual(len(created), len(DEFAULT_EMAIL_TEMPLATES))
        self.assertEqual(
            EmailTemplate.objects.filter(organization=self.org).count(),
            len(DEFAULT_EMAIL_TEMPLATES),
        )
        row = EmailTemplate.objects.get(organization=self.org, code="sales_message")
        row.body_text = "Custom wording"
        row.save(update_fields=["body_text"])
        EmailTemplate.objects.get(organization=self.org, code="general_message").delete()

        again = ensure_default_email_templates(self.org)
        self.assertEqual(again, ["general_message"])
        kept = EmailTemplate.objects.get(organization=self.org, code="sales_message")
        self.assertEqual(kept.body_text, "Custom wording")
        restored = EmailTemplate.objects.get(organization=self.org, code="general_message")
        self.assertIn("{{recipient}}", restored.body_text)
        self.assertIn("{{title}}", restored.subject)

    def test_template_list_seeds_the_starter_set(self):
        response = self.client.get("/api/settings/email-templates/")
        self.assertEqual(response.status_code, 200, response.content)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        codes = {row["code"] for row in rows}
        self.assertIn("action_required", codes)
        self.assertIn("payroll_notice", codes)
        self.assertGreaterEqual(len(codes), len(DEFAULT_EMAIL_TEMPLATES))
