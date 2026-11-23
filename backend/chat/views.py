"""Tenant-internal chat. Rooms never cross organizations."""

import os

from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from chat.models import ChatMembership, ChatMessage, ChatRoom
from core.access import user_organization
from core.tenancy import _abs_media

BODY_MAX = 4000
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
FILE_EXT = IMAGE_EXT | {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".csv"}


def _name(user) -> str:
    if user is None:
        return "Someone"
    full = (user.get_full_name() or "").strip()
    return full or user.username


def _org_user(org, user_id):
    profile = (
        UserProfile.objects.filter(
            organization=org,
            user_id=user_id,
            is_active_member=True,
            user__is_active=True,
        )
        .select_related("user")
        .first()
    )
    return profile.user if profile else None


def _membership(room, user):
    return ChatMembership.objects.filter(room=room, user=user, is_deleted=False).first()


def _active(room, user):
    row = _membership(room, user)
    if row is None or row.status != ChatMembership.Status.ACTIVE:
        return None
    return row


def _can_manage(row) -> bool:
    return bool(
        row
        and row.status == ChatMembership.Status.ACTIVE
        and row.role in {ChatMembership.Role.OWNER, ChatMembership.Role.ADMIN}
    )


def _room_for(org, user, room_id):
    room = ChatRoom.objects.filter(organization=org, pk=room_id, is_deleted=False).first()
    if room is None:
        return None, None
    return room, _membership(room, user)


def _touch(room):
    ChatRoom.objects.filter(pk=room.pk).update(updated_at=timezone.now())


def _system(room, body: str):
    ChatMessage.objects.create(room=room, kind=ChatMessage.Kind.SYSTEM, body=body[:BODY_MAX])
    _touch(room)


def _notify_invite(org, room, people, inviter):
    from notifications.services import push_inbox

    label = room.name or "a conversation"
    push_inbox(
        org,
        people,
        title=f"Chat invite: {label}",
        body=f"{_name(inviter)} invited you to {label}. Accept it in Chat.",
        href=f"/chat?room={room.pk}",
        module="chat",
        object_id=room.pk,
        kind="chat",
    )


def _member_payload(row: ChatMembership) -> dict:
    return {
        "user_id": row.user_id,
        "name": _name(row.user),
        "username": row.user.username,
        "role": row.role,
        "status": row.status,
        "muted": row.muted,
    }


def _last_message(room):
    message = (
        ChatMessage.objects.filter(room=room, is_deleted=False)
        .select_related("sender")
        .order_by("-id")
        .first()
    )
    if message is None:
        return None
    body = "Message removed" if message.removed else message.body
    return {
        "id": message.pk,
        "body": body[:180],
        "kind": message.kind,
        "sender_name": _name(message.sender) if message.kind == ChatMessage.Kind.TEXT else "",
        "created_at": _iso(message.created_at),
        "sent_label": _sent_label(message.created_at),
    }


def _room_payload(room: ChatRoom, mine: ChatMembership, viewer) -> dict:
    members = list(
        ChatMembership.objects.filter(room=room, is_deleted=False)
        .exclude(status__in=[ChatMembership.Status.DECLINED, ChatMembership.Status.REMOVED])
        .select_related("user")
    )
    title = room.name
    if room.kind == ChatRoom.Kind.DIRECT:
        other = next((row for row in members if row.user_id != viewer.id), None)
        title = _name(other.user) if other else "Direct message"
    unread = 0
    if mine.status == ChatMembership.Status.ACTIVE and not mine.muted:
        qs = ChatMessage.objects.filter(
            room=room, kind=ChatMessage.Kind.TEXT, removed=False, is_deleted=False
        ).exclude(sender=viewer)
        if mine.last_read_at:
            qs = qs.filter(created_at__gt=mine.last_read_at)
        unread = qs.count()
    return {
        "id": room.pk,
        "kind": room.kind,
        "name": title,
        "topic": room.topic,
        "my_role": mine.role,
        "my_status": mine.status,
        "muted": mine.muted,
        "unread": unread,
        "members": [_member_payload(row) for row in members],
        "last_message": _last_message(room),
        "updated_at": room.updated_at,
    }


def _iso(value) -> str:
    if not value:
        return ""
    try:
        return value.isoformat()
    except Exception:
        return ""


def _sent_label(value) -> str:
    if not value:
        return ""
    try:
        local = timezone.localtime(value)
    except Exception:
        return ""
    return local.strftime("%d-%m-%Y %H:%M")


def _as_bool(value, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _message_payload(message: ChatMessage, request=None) -> dict:
    reply = None
    if message.reply_to_id and message.reply_to and not message.reply_to.is_deleted:
        reply = {
            "id": message.reply_to_id,
            "body": "Message removed" if message.reply_to.removed else message.reply_to.body[:180],
            "sender_name": _name(message.reply_to.sender),
        }
    url, name, kind = _attachment(message, request)
    return {
        "id": message.pk,
        "sender_id": message.sender_id,
        "sender_name": _name(message.sender) if message.kind == ChatMessage.Kind.TEXT else "",
        "body": "" if message.removed else message.body,
        "kind": message.kind,
        "removed": message.removed,
        "edited_at": _iso(message.edited_at),
        "created_at": _iso(message.created_at),
        "sent_label": _sent_label(message.created_at),
        "attachment_url": url,
        "attachment_name": name,
        "attachment_kind": kind,
        "reply_to": reply,
    }


def _attachment(message: ChatMessage, request=None) -> tuple[str, str, str]:
    file = getattr(message, "attachment", None)
    if not file:
        return "", "", ""
    try:
        url = file.url or ""
    except Exception:
        url = ""
    absolute = _abs_media(file, request) or ""
    if absolute.startswith("https://"):
        url = absolute
    name = os.path.basename(getattr(file, "name", "") or "")
    ext = os.path.splitext(name)[1].lower()
    kind = "image" if ext in IMAGE_EXT else "file"
    return url, name, kind


def _allowed_upload(upload) -> str:
    name = os.path.basename(getattr(upload, "name", "") or "")
    ext = os.path.splitext(name)[1].lower()
    if ext not in FILE_EXT:
        return "Attach a picture (JPG, PNG, GIF, WEBP) or a document (PDF, Word, Excel, TXT, CSV)."
    return ""


def _ids(data, key="user_ids") -> list[int]:
    raw = data.get(key) if isinstance(data, dict) else None
    if raw is None and key == "user_ids":
        raw = data.get("user_id") if isinstance(data, dict) else None
        raw = [raw] if raw else []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[:50]:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


class ChatPeopleView(APIView):
    rbac_module = "chat"

    def get(self, request):
        org = user_organization(request.user)
        if not org:
            return Response([])
        q = (request.query_params.get("q") or "").strip()
        qs = UserProfile.objects.filter(
            organization=org, is_active_member=True, user__is_active=True
        ).select_related("user")
        if q:
            qs = qs.filter(
                Q(user__username__icontains=q)
                | Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
            )
        rows = []
        for profile in qs.order_by("user__first_name", "user__username")[:30]:
            if profile.user_id == request.user.id:
                continue
            rows.append(
                {
                    "id": profile.user_id,
                    "name": _name(profile.user),
                    "username": profile.user.username,
                }
            )
        return Response(rows)


class ChatRoomsView(APIView):
    rbac_module = "chat"

    def get(self, request):
        org = user_organization(request.user)
        if not org:
            return Response([])
        now = timezone.now()
        mine = list(
            ChatMembership.objects.filter(
                user=request.user,
                is_deleted=False,
                status__in=[ChatMembership.Status.INVITED, ChatMembership.Status.ACTIVE],
                room__organization=org,
                room__is_deleted=False,
            )
            .select_related("room")
            .order_by("-room__updated_at")[:100]
        )
        active_ids = [row.pk for row in mine if row.status == ChatMembership.Status.ACTIVE]
        if active_ids:
            ChatMembership.objects.filter(pk__in=active_ids).update(last_seen_at=now)
        return Response([_room_payload(row.room, row, request.user) for row in mine])

    def post(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        name = str(request.data.get("name") or "").strip()[:80]
        topic = str(request.data.get("topic") or "").strip()[:180]
        if not name:
            return Response({"detail": "A group needs a name."}, status=400)
        people = []
        for user_id in _ids(request.data):
            if user_id == request.user.id:
                continue
            person = _org_user(org, user_id)
            if person is None:
                return Response({"detail": "That person is not in this organization."}, status=400)
            people.append(person)
        room = ChatRoom.objects.create(
            organization=org,
            kind=ChatRoom.Kind.GROUP,
            name=name,
            topic=topic,
            created_by=request.user,
        )
        ChatMembership.objects.create(
            room=room,
            user=request.user,
            role=ChatMembership.Role.OWNER,
            status=ChatMembership.Status.ACTIVE,
            last_read_at=timezone.now(),
            created_by=request.user,
        )
        invited = []
        for person in people:
            ChatMembership.objects.create(
                room=room,
                user=person,
                role=ChatMembership.Role.MEMBER,
                status=ChatMembership.Status.INVITED,
                invited_by=request.user,
                created_by=request.user,
            )
            invited.append(person)
        _system(room, f"{_name(request.user)} created {name}.")
        if invited:
            names = ", ".join(_name(person) for person in invited[:8])
            _system(room, f"{_name(request.user)} invited {names}.")
            _notify_invite(org, room, invited, request.user)
        mine = _membership(room, request.user)
        return Response(_room_payload(room, mine, request.user), status=201)


class ChatDirectView(APIView):
    rbac_module = "chat"

    def post(self, request):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        try:
            user_id = int(request.data.get("user_id"))
        except (TypeError, ValueError):
            return Response({"detail": "Choose a colleague."}, status=400)
        if user_id == request.user.id:
            return Response({"detail": "Choose a colleague."}, status=400)
        other = _org_user(org, user_id)
        if other is None:
            return Response({"detail": "That person is not in this organization."}, status=400)
        pair = ":".join(str(item) for item in sorted((request.user.id, other.id)))
        room = ChatRoom.objects.filter(
            organization=org, kind=ChatRoom.Kind.DIRECT, direct_key=pair, is_deleted=False
        ).first()
        if room is None:
            room = ChatRoom.objects.create(
                organization=org,
                kind=ChatRoom.Kind.DIRECT,
                direct_key=pair,
                created_by=request.user,
            )
            ChatMembership.objects.create(
                room=room,
                user=request.user,
                role=ChatMembership.Role.MEMBER,
                status=ChatMembership.Status.ACTIVE,
                created_by=request.user,
            )
            ChatMembership.objects.create(
                room=room,
                user=other,
                role=ChatMembership.Role.MEMBER,
                status=ChatMembership.Status.ACTIVE,
                created_by=request.user,
            )
        else:
            for person in (request.user, other):
                row = _membership(room, person)
                if row is None:
                    ChatMembership.objects.create(
                        room=room,
                        user=person,
                        role=ChatMembership.Role.MEMBER,
                        status=ChatMembership.Status.ACTIVE,
                        created_by=request.user,
                    )
                elif row.status != ChatMembership.Status.ACTIVE:
                    row.status = ChatMembership.Status.ACTIVE
                    row.save(update_fields=["status", "updated_at"])
        mine = _membership(room, request.user)
        return Response(_room_payload(room, mine, request.user))


class ChatRoomDetailView(APIView):
    rbac_module = "chat"

    def patch(self, request, room_id):
        org = user_organization(request.user)
        room, mine = _room_for(org, request.user, room_id)
        if room is None or mine is None:
            return Response({"detail": "Not found."}, status=404)
        if room.kind != ChatRoom.Kind.GROUP or not _can_manage(mine):
            return Response({"detail": "Only a group owner or admin can change this."}, status=403)
        name = str(request.data.get("name") or room.name).strip()[:80]
        topic = str(request.data.get("topic") if "topic" in request.data else room.topic).strip()[:180]
        if not name:
            return Response({"detail": "A group needs a name."}, status=400)
        renamed = name != room.name
        room.name = name
        room.topic = topic
        room.updated_by = request.user
        room.save(update_fields=["name", "topic", "updated_by", "updated_at"])
        if renamed:
            _system(room, f"{_name(request.user)} renamed the group to {name}.")
        return Response(_room_payload(room, mine, request.user))

    def post(self, request, room_id, action):
        org = user_organization(request.user)
        room, mine = _room_for(org, request.user, room_id)
        if room is None or mine is None:
            return Response({"detail": "Not found."}, status=404)
        handler = {
            "invite": self._invite,
            "accept": self._accept,
            "decline": self._decline,
            "leave": self._leave,
            "mute": self._mute,
        }.get(action)
        if handler is None:
            return Response({"detail": "Unknown action."}, status=404)
        return handler(request, org, room, mine)

    def _invite(self, request, org, room, mine):
        if room.kind != ChatRoom.Kind.GROUP or not _can_manage(mine):
            return Response({"detail": "Only a group owner or admin can invite."}, status=403)
        wanted = []
        for user_id in _ids(request.data):
            if user_id == request.user.id:
                continue
            person = _org_user(org, user_id)
            if person is None:
                return Response({"detail": "That person is not in this organization."}, status=400)
            wanted.append(person)
        invited = []
        for person in wanted:
            row = _membership(room, person)
            if row and row.status in {ChatMembership.Status.ACTIVE, ChatMembership.Status.INVITED}:
                continue
            if row is None:
                ChatMembership.objects.create(
                    room=room,
                    user=person,
                    role=ChatMembership.Role.MEMBER,
                    status=ChatMembership.Status.INVITED,
                    invited_by=request.user,
                    created_by=request.user,
                )
            else:
                row.status = ChatMembership.Status.INVITED
                row.role = ChatMembership.Role.MEMBER
                row.invited_by = request.user
                row.save(update_fields=["status", "role", "invited_by", "updated_at"])
            invited.append(person)
        if invited:
            names = ", ".join(_name(person) for person in invited[:8])
            _system(room, f"{_name(request.user)} invited {names}.")
            _notify_invite(org, room, invited, request.user)
        return Response(_room_payload(room, mine, request.user))

    def _accept(self, request, org, room, mine):
        if mine.status != ChatMembership.Status.INVITED:
            return Response({"detail": "There is no invite to accept."}, status=400)
        mine.status = ChatMembership.Status.ACTIVE
        mine.last_read_at = timezone.now()
        mine.save(update_fields=["status", "last_read_at", "updated_at"])
        _system(room, f"{_name(request.user)} joined.")
        return Response(_room_payload(room, mine, request.user))

    def _decline(self, request, org, room, mine):
        if mine.status != ChatMembership.Status.INVITED:
            return Response({"detail": "There is no invite to decline."}, status=400)
        mine.status = ChatMembership.Status.DECLINED
        mine.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Invite declined."})

    def _leave(self, request, org, room, mine):
        if room.kind == ChatRoom.Kind.DIRECT:
            mine.status = ChatMembership.Status.LEFT
            mine.save(update_fields=["status", "updated_at"])
            return Response({"detail": "Conversation hidden."})
        if mine.status != ChatMembership.Status.ACTIVE:
            return Response({"detail": "You are not in this group."}, status=400)
        if mine.role == ChatMembership.Role.OWNER:
            successor = (
                ChatMembership.objects.filter(
                    room=room,
                    status=ChatMembership.Status.ACTIVE,
                    is_deleted=False,
                )
                .exclude(user=request.user)
                .order_by("role", "id")
                .first()
            )
            if successor:
                successor.role = ChatMembership.Role.OWNER
                successor.save(update_fields=["role", "updated_at"])
        mine.status = ChatMembership.Status.LEFT
        mine.role = ChatMembership.Role.MEMBER
        mine.save(update_fields=["status", "role", "updated_at"])
        _system(room, f"{_name(request.user)} left.")
        return Response({"detail": "You left the group."})

    def _mute(self, request, org, room, mine):
        if mine.status != ChatMembership.Status.ACTIVE:
            return Response({"detail": "Join the conversation first."}, status=400)
        mine.muted = _as_bool(request.data.get("muted"), not mine.muted)
        mine.save(update_fields=["muted", "updated_at"])
        return Response(_room_payload(room, mine, request.user))


class ChatMemberView(APIView):
    rbac_module = "chat"

    def post(self, request, room_id, user_id, action):
        org = user_organization(request.user)
        room, mine = _room_for(org, request.user, room_id)
        if room is None or not _can_manage(mine):
            return Response({"detail": "Not found."}, status=404)
        if room.kind != ChatRoom.Kind.GROUP:
            return Response({"detail": "Direct conversations stay between two people."}, status=400)
        target = ChatMembership.objects.filter(
            room=room, user_id=user_id, is_deleted=False
        ).select_related("user").first()
        if target is None:
            return Response({"detail": "Not a member."}, status=404)
        if action == "remove":
            if target.user_id == request.user.id:
                return Response({"detail": "Use leave for yourself."}, status=400)
            if target.role == ChatMembership.Role.OWNER:
                return Response({"detail": "The owner cannot be removed."}, status=400)
            if target.role == ChatMembership.Role.ADMIN and mine.role != ChatMembership.Role.OWNER:
                return Response({"detail": "Only the owner can remove an admin."}, status=403)
            target.status = ChatMembership.Status.REMOVED
            target.save(update_fields=["status", "updated_at"])
            _system(room, f"{_name(request.user)} removed {_name(target.user)}.")
            return Response(_room_payload(room, mine, request.user))
        if action == "role":
            if mine.role != ChatMembership.Role.OWNER:
                return Response({"detail": "Only the owner can change roles."}, status=403)
            role = str(request.data.get("role") or "")
            if role not in {ChatMembership.Role.ADMIN, ChatMembership.Role.MEMBER, ChatMembership.Role.OWNER}:
                return Response({"detail": "Choose owner, admin, or member."}, status=400)
            if target.user_id == request.user.id and role != ChatMembership.Role.OWNER:
                return Response({"detail": "Hand the group to someone else first."}, status=400)
            if role == ChatMembership.Role.OWNER:
                mine.role = ChatMembership.Role.ADMIN
                mine.save(update_fields=["role", "updated_at"])
            target.role = role
            if target.status != ChatMembership.Status.ACTIVE:
                return Response({"detail": "They need to accept the invite first."}, status=400)
            target.save(update_fields=["role", "updated_at"])
            _system(room, f"{_name(target.user)} is now {role}.")
            return Response(_room_payload(room, mine, request.user))
        return Response({"detail": "Unknown action."}, status=404)


class ChatMessagesView(APIView):
    rbac_module = "chat"

    def get(self, request, room_id):
        org = user_organization(request.user)
        room, mine = _room_for(org, request.user, room_id)
        if room is None or mine is None or mine.status != ChatMembership.Status.ACTIVE:
            return Response({"detail": "Not found."}, status=404)
        qs = ChatMessage.objects.filter(room=room, is_deleted=False).select_related(
            "sender", "reply_to", "reply_to__sender"
        )
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(kind=ChatMessage.Kind.TEXT, removed=False, body__icontains=q)
        before = request.query_params.get("before")
        if before:
            try:
                qs = qs.filter(id__lt=int(before))
            except (TypeError, ValueError):
                pass
        rows = list(qs.order_by("-id")[:50])
        rows.reverse()
        mine.last_read_at = timezone.now()
        mine.save(update_fields=["last_read_at", "updated_at"])
        return Response([_message_payload(row, request) for row in rows])

    def post(self, request, room_id):
        org = user_organization(request.user)
        room, mine = _room_for(org, request.user, room_id)
        if mine is None or mine.status != ChatMembership.Status.ACTIVE:
            return Response({"detail": "Not found."}, status=404)
        body = str(request.data.get("body") or "").strip()
        upload = request.FILES.get("attachment")
        if not body and not upload:
            return Response({"detail": "Write a message or attach a file."}, status=400)
        if len(body) > BODY_MAX:
            return Response({"detail": "Message is too long."}, status=400)
        if upload and getattr(upload, "size", 0) > 8 * 1024 * 1024:
            return Response({"detail": "Attachments must be 8 MB or smaller."}, status=400)
        if upload:
            rejected = _allowed_upload(upload)
            if rejected:
                return Response({"detail": rejected}, status=400)
        reply = None
        reply_id = request.data.get("reply_to")
        if reply_id:
            reply = ChatMessage.objects.filter(room=room, pk=reply_id, is_deleted=False).first()
        message = ChatMessage.objects.create(
            room=room,
            sender=request.user,
            body=body,
            reply_to=reply,
            attachment=upload,
            created_by=request.user,
        )
        mine.last_read_at = timezone.now()
        mine.save(update_fields=["last_read_at", "updated_at"])
        _touch(room)
        message.reply_to = reply
        return Response(_message_payload(message, request), status=201)


class ChatMessageDetailView(APIView):
    rbac_module = "chat"

    def patch(self, request, message_id):
        return self._edit(request, message_id)

    def post(self, request, message_id):
        return self._remove(request, message_id)

    def _load(self, request, message_id):
        org = user_organization(request.user)
        message = (
            ChatMessage.objects.filter(pk=message_id, is_deleted=False, room__organization=org)
            .select_related("room", "sender", "reply_to", "reply_to__sender")
            .first()
        )
        if message is None:
            return None, None
        mine = _active(message.room, request.user)
        if mine is None:
            return None, None
        return message, mine

    def _edit(self, request, message_id):
        message, mine = self._load(request, message_id)
        if message is None:
            return Response({"detail": "Not found."}, status=404)
        if message.kind != ChatMessage.Kind.TEXT or message.removed or message.sender_id != request.user.id:
            return Response({"detail": "You can edit only your own messages."}, status=403)
        body = str(request.data.get("body") or "").strip()
        if not body or len(body) > BODY_MAX:
            return Response({"detail": "Write a message."}, status=400)
        message.body = body
        message.edited_at = timezone.now()
        message.updated_by = request.user
        message.save(update_fields=["body", "edited_at", "updated_by", "updated_at"])
        return Response(_message_payload(message, request))

    def _remove(self, request, message_id):
        message, mine = self._load(request, message_id)
        if message is None:
            return Response({"detail": "Not found."}, status=404)
        if message.kind != ChatMessage.Kind.TEXT or message.removed:
            return Response({"detail": "That message is already gone."}, status=400)
        if message.sender_id != request.user.id and not _can_manage(mine):
            return Response({"detail": "You cannot remove that message."}, status=403)
        message.removed = True
        message.body = ""
        message.updated_by = request.user
        message.save(update_fields=["removed", "body", "updated_by", "updated_at"])
        return Response(_message_payload(message, request))
