from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization


class ChatTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme-chat",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        self.other_org = Organization.objects.create(
            name="Other",
            code="other-chat",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        ensure_default_roles(self.org)
        ensure_default_roles(self.other_org)
        User = get_user_model()
        self.owner = self._user(User, "chat-owner", self.org, UserProfile.RoleCode.OWNER)
        self.org.owner = self.owner
        self.org.save()
        self.ada = self._user(User, "chat-ada", self.org, UserProfile.RoleCode.HR)
        self.bo = self._user(User, "chat-bo", self.org, UserProfile.RoleCode.FINANCE)
        self.outsider = self._user(User, "chat-out", self.other_org, UserProfile.RoleCode.ADMIN)
        self.client = APIClient()

    def _user(self, User, username, org, role):
        user = User.objects.create_user(username, password="x-long-password-1", first_name=username)
        UserProfile.objects.create(user=user, organization=org, role=role)
        return user

    def test_direct_message_stays_inside_the_tenant(self):
        self.client.force_authenticate(self.owner)
        opened = self.client.post("/api/chat/direct/", {"user_id": self.ada.id})
        self.assertEqual(opened.status_code, 200, opened.content)
        room_id = opened.data["id"]
        sent = self.client.post(f"/api/chat/rooms/{room_id}/messages/", {"body": "Hello Ada"})
        self.assertEqual(sent.status_code, 201, sent.content)

        self.client.force_authenticate(self.ada)
        inbox = self.client.get("/api/chat/rooms/")
        self.assertEqual(inbox.data[0]["id"], room_id)
        self.assertGreaterEqual(inbox.data[0]["unread"], 1)
        thread = self.client.get(f"/api/chat/rooms/{room_id}/messages/")
        self.assertEqual(thread.data[-1]["body"], "Hello Ada")

        self.client.force_authenticate(self.outsider)
        hidden = self.client.get(f"/api/chat/rooms/{room_id}/messages/")
        self.assertEqual(hidden.status_code, 404)
        blocked = self.client.post("/api/chat/direct/", {"user_id": self.ada.id})
        self.assertEqual(blocked.status_code, 400)

    def test_group_invite_must_be_accepted(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            "/api/chat/rooms/",
            {"name": "Payroll desk", "topic": "Runs", "user_ids": [self.ada.id, self.bo.id]},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        room_id = created.data["id"]
        self.assertEqual(created.data["my_role"], "owner")

        self.client.force_authenticate(self.ada)
        pending = self.client.get("/api/chat/rooms/")
        self.assertEqual(pending.data[0]["my_status"], "invited")
        blocked = self.client.get(f"/api/chat/rooms/{room_id}/messages/")
        self.assertEqual(blocked.status_code, 404)
        accepted = self.client.post(f"/api/chat/rooms/{room_id}/accept/")
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertEqual(accepted.data["my_status"], "active")

        self.client.force_authenticate(self.bo)
        declined = self.client.post(f"/api/chat/rooms/{room_id}/decline/")
        self.assertEqual(declined.status_code, 200)
        gone = self.client.get("/api/chat/rooms/")
        self.assertEqual(gone.data, [])

        self.client.force_authenticate(self.ada)
        sent = self.client.post(f"/api/chat/rooms/{room_id}/messages/", {"body": "Joined"})
        self.assertEqual(sent.status_code, 201, sent.content)
        edited = self.client.patch(f"/api/chat/messages/{sent.data['id']}/", {"body": "Joined in"})
        self.assertEqual(edited.status_code, 200, edited.content)
        self.assertEqual(edited.data["body"], "Joined in")

        self.client.force_authenticate(self.owner)
        renamed = self.client.patch(f"/api/chat/rooms/{room_id}/", {"name": "Payroll room", "topic": "Runs"})
        self.assertEqual(renamed.status_code, 200, renamed.content)
        removed = self.client.post(f"/api/chat/messages/{sent.data['id']}/remove/")
        self.assertEqual(removed.status_code, 200, removed.content)
        self.assertTrue(removed.data["removed"])

    def test_member_cannot_invite_and_outsider_is_rejected(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post("/api/chat/rooms/", {"name": "Owners", "user_ids": [self.ada.id]}, format="json")
        room_id = created.data["id"]
        self.client.force_authenticate(self.ada)
        self.client.post(f"/api/chat/rooms/{room_id}/accept/")
        denied = self.client.post(f"/api/chat/rooms/{room_id}/invite/", {"user_ids": [self.bo.id]}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.owner)
        foreign = self.client.post(
            f"/api/chat/rooms/{room_id}/invite/",
            {"user_ids": [self.outsider.id]},
            format="json",
        )
        self.assertEqual(foreign.status_code, 400)
