from django.conf import settings
from django.db import models

from core.models import AuditModel, Organization


class ChatRoom(AuditModel):
    class Kind(models.TextChoices):
        DIRECT = "direct", "Direct"
        GROUP = "group", "Group"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="chat_rooms"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.GROUP)
    name = models.CharField(max_length=80, blank=True, default="")
    topic = models.CharField(max_length=180, blank=True, default="")
    direct_key = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "direct_key"],
                condition=~models.Q(direct_key=""),
                name="chat_room_direct_pair",
            )
        ]


class ChatMembership(AuditModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"

    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        ACTIVE = "active", "Active"
        DECLINED = "declined", "Declined"
        LEFT = "left", "Left"
        REMOVED = "removed", "Removed"

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.INVITED)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_invites_sent",
    )
    last_read_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    muted = models.BooleanField(default=False)

    class Meta:
        unique_together = ("room", "user")
        ordering = ["id"]


class ChatMessage(AuditModel):
    class Kind(models.TextChoices):
        TEXT = "text", "Text"
        SYSTEM = "system", "System"

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="chat_messages",
    )
    body = models.TextField(blank=True, default="")
    attachment = models.FileField(upload_to="chat/%Y/%m/", blank=True, null=True)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.TEXT)
    edited_at = models.DateTimeField(null=True, blank=True)
    removed = models.BooleanField(default=False)
    reply_to = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies"
    )

    class Meta:
        ordering = ["id"]
