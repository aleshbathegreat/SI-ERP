from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme-reset",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=14),
        )
        User = get_user_model()
        self.user = User.objects.create_user(
            "reset-owner",
            email="owner@acme-reset.test",
            password="Old-password-1",
            first_name="Ada",
        )
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save(update_fields=["owner"])
        ensure_default_roles(self.org)
        self.client = APIClient()

    def test_unknown_email_does_not_send(self):
        with patch("core.notifications.notify_system", return_value=True) as mail:
            res = self.client.post(
                "/api/auth/password-reset/",
                {"email": "missing@acme-reset.test"},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        mail.assert_not_called()

    def test_reset_link_sets_a_new_password(self):
        with patch("core.notifications.notify_system", return_value=True) as mail:
            res = self.client.post(
                "/api/auth/password-reset/",
                {"email": "owner@acme-reset.test"},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        body = mail.call_args[0][1]
        self.assertIn("reset-owner", body)
        link = next(line for line in body.splitlines() if "/reset-password?" in line)
        query = link.split("?", 1)[1]
        parts = dict(item.split("=", 1) for item in query.split("&"))
        bad = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"uid": parts["uid"], "token": "nope", "password": "New-password-2"},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"uid": parts["uid"], "token": parts["token"], "password": "New-password-2"},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-password-2"))
        login = self.client.post(
            "/api/auth/login/",
            {"username": "reset-owner", "password": "New-password-2"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)

    def test_signup_welcome_uses_platform_mail(self):
        with patch("core.notifications.notify_system", return_value=True) as mail:
            res = self.client.post(
                "/api/saas/signup/",
                {
                    "company_name": "Mail Check Co",
                    "username": "mail-check-owner",
                    "email": "signup@acme-reset.test",
                    "password": "Signup-password-1",
                    "first_name": "Sam",
                },
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        subject, message, recipients = mail.call_args[0]
        self.assertIn("Welcome", subject)
        self.assertIn("mail-check-owner", message)
        self.assertEqual(recipients, ["signup@acme-reset.test"])

    def test_invite_sends_account_mail(self):
        self.client.force_authenticate(self.user)
        with patch("core.notifications.notify_user", return_value=True) as mail:
            res = self.client.post(
                "/api/settings/users/invite/",
                {
                    "username": "invited-clerk",
                    "password": "Invite-password-1",
                    "email": "clerk@acme-reset.test",
                    "first_name": "Cleo",
                },
                format="json",
            )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(mail.call_args[0][0].username, "invited-clerk")
        self.assertIn("added to", mail.call_args[0][2])
