import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0017_mailbox_profiles"),
        ("accounts", "0007_role_soft_delete"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatRoom",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("kind", models.CharField(choices=[("direct", "Direct"), ("group", "Group")], default="group", max_length=16)),
                ("name", models.CharField(blank=True, default="", max_length=80)),
                ("topic", models.CharField(blank=True, default="", max_length=180)),
                ("direct_key", models.CharField(blank=True, default="", max_length=64)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_rooms", to="core.organization")),
            ],
            options={"ordering": ["-updated_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="chatroom",
            constraint=models.UniqueConstraint(condition=~models.Q(direct_key=""), fields=("organization", "direct_key"), name="chat_room_direct_pair"),
        ),
        migrations.CreateModel(
            name="ChatMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("role", models.CharField(choices=[("owner", "Owner"), ("admin", "Admin"), ("member", "Member")], default="member", max_length=16)),
                ("status", models.CharField(choices=[("invited", "Invited"), ("active", "Active"), ("declined", "Declined"), ("left", "Left"), ("removed", "Removed")], default="invited", max_length=16)),
                ("last_read_at", models.DateTimeField(blank=True, null=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("muted", models.BooleanField(default=False)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("invited_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chat_invites_sent", to=settings.AUTH_USER_MODEL)),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="chat.chatroom")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["id"], "unique_together": {("room", "user")}},
        ),
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_deleted", models.BooleanField(db_index=True, default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("body", models.TextField(blank=True, default="")),
                ("kind", models.CharField(choices=[("text", "Text"), ("system", "System")], default="text", max_length=16)),
                ("edited_at", models.DateTimeField(blank=True, null=True)),
                ("removed", models.BooleanField(default=False)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_created", to=settings.AUTH_USER_MODEL)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_updated", to=settings.AUTH_USER_MODEL)),
                ("deleted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deleted", to=settings.AUTH_USER_MODEL)),
                ("reply_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="replies", to="chat.chatmessage")),
                ("room", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chat.chatroom")),
                ("sender", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="chat_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["id"]},
        ),
    ]
