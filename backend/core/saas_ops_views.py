"""SaaS invoices, support tickets, platform staff APIs."""

from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.access import extend_subscription, user_organization
from core.bulk import BulkDeleteMixin
from core.invoicing import create_invoice, mark_invoice_paid
from core.models import (
    Organization,
    PlatformStaff,
    SaaSInvoice,
    SubscriptionPackage,
    SupportTicket,
    SupportTicketMessage,
)
from core.platform_rbac import (
    ROLE_CAPS,
    has_platform_cap,
    is_platform_user,
    platform_capabilities,
    platform_role,
    require_platform_cap,
)
from core.serializers import (
    PlatformStaffSerializer,
    SaaSInvoiceSerializer,
    SupportTicketMessageSerializer,
    SupportTicketSerializer,
)


def _ticket_no() -> str:
    year = date.today().year
    prefix = f"TK-{year}-"
    last = (
        SupportTicket.objects.filter(ticket_no__startswith=prefix)
        .order_by("-ticket_no")
        .values_list("ticket_no", flat=True)
        .first()
    )
    seq = 1
    if last:
        try:
            seq = int(last.split("-")[-1]) + 1
        except ValueError:
            seq = SupportTicket.objects.count() + 1
    return f"{prefix}{seq:05d}"


class TenantInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """Tenant-facing SaaS invoices (subscription AR)."""

    serializer_class = SaaSInvoiceSerializer
    permission_classes = [IsAuthenticated]
    rbac_module = "billing"
    subscription_exempt = True
    pagination_class = None

    def get_queryset(self):
        org = user_organization(self.request.user)
        if not org:
            return SaaSInvoice.objects.none()
        return SaaSInvoice.objects.filter(organization=org).select_related(
            "package", "payment"
        )


class PlatformInvoiceViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
    serializer_class = SaaSInvoiceSerializer
    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True
    pagination_class = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        err = require_platform_cap(request.user, "invoices")
        if err:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(err[0]["detail"])

    def get_queryset(self):
        qs = SaaSInvoice.objects.select_related(
            "organization", "package", "payment"
        ).order_by("-id")
        org_id = self.request.query_params.get("organization")
        st = self.request.query_params.get("status")
        if org_id:
            qs = qs.filter(organization_id=org_id)
        if st:
            qs = qs.filter(status=st)
        return qs

    def create(self, request, *args, **kwargs):
        org = Organization.objects.filter(pk=request.data.get("organization")).first()
        if not org:
            return Response({"detail": "organization required"}, status=400)
        pkg = None
        plan_code = request.data.get("plan_code") or ""
        if plan_code:
            pkg = SubscriptionPackage.objects.filter(code=plan_code).first()
        inv = create_invoice(
            org,
            amount=request.data.get("amount") or 0,
            plan_code=plan_code,
            package=pkg,
            period_start=request.data.get("period_start") or None,
            period_end=request.data.get("period_end") or None,
            description=request.data.get("description") or "",
            tax_amount=request.data.get("tax_amount") or 0,
            due_days=int(request.data.get("due_days") or 14),
            status=request.data.get("status") or SaaSInvoice.Status.SENT,
            user=request.user,
            notes=request.data.get("notes") or "",
        )
        return Response(SaaSInvoiceSerializer(inv).data, status=201)

    @action(detail=True, methods=["post"])
    def mark_paid(self, request, pk=None):
        err = require_platform_cap(request.user, "invoices.mark_paid")
        if err:
            return Response(err[0], status=err[1])
        inv = self.get_object()
        mark_invoice_paid(inv)
        return Response(SaaSInvoiceSerializer(inv).data)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        inv = self.get_object()
        if inv.status == SaaSInvoice.Status.PAID:
            return Response({"detail": "Cannot void a paid invoice"}, status=400)
        inv.status = SaaSInvoice.Status.VOID
        inv.save(update_fields=["status", "updated_at"])
        return Response(SaaSInvoiceSerializer(inv).data)


class TenantTicketViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True
    pagination_class = None
    http_method_names = ["get", "post", "patch", "head", "options", "delete"]

    def get_queryset(self):
        org = user_organization(self.request.user)
        if not org:
            return SupportTicket.objects.none()
        return SupportTicket.objects.filter(organization=org).prefetch_related(
            "messages"
        )

    def create(self, request, *args, **kwargs):
        org = user_organization(request.user)
        if not org:
            return Response({"detail": "No organization"}, status=400)
        subject = (request.data.get("subject") or "").strip()
        body = (request.data.get("body") or "").strip()
        if not subject or not body:
            return Response({"detail": "subject and body required"}, status=400)
        ticket = SupportTicket.objects.create(
            organization=org,
            ticket_no=_ticket_no(),
            subject=subject[:200],
            category=request.data.get("category") or SupportTicket.Category.GENERAL,
            priority=request.data.get("priority") or SupportTicket.Priority.NORMAL,
            created_by=request.user,
            last_message_at=timezone.now(),
        )
        SupportTicketMessage.objects.create(
            ticket=ticket,
            author=request.user,
            body=body,
            is_from_platform=False,
        )
        return Response(SupportTicketSerializer(ticket).data, status=201)

    def partial_update(self, request, *args, **kwargs):
        ticket = self.get_object()
        # Tenant may only close their ticket
        if "status" in request.data and request.data["status"] in (
            SupportTicket.Status.CLOSED,
            SupportTicket.Status.RESOLVED,
        ):
            ticket.status = request.data["status"]
            ticket.save(update_fields=["status", "updated_at"])
        return Response(SupportTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "body required"}, status=400)
        if ticket.status == SupportTicket.Status.CLOSED:
            return Response({"detail": "Ticket closed"}, status=400)
        msg = SupportTicketMessage.objects.create(
            ticket=ticket,
            author=request.user,
            body=body,
            is_from_platform=False,
        )
        ticket.last_message_at = timezone.now()
        if ticket.status == SupportTicket.Status.WAITING:
            ticket.status = SupportTicket.Status.OPEN
        ticket.save(update_fields=["last_message_at", "status", "updated_at"])
        return Response(SupportTicketMessageSerializer(msg).data, status=201)


class PlatformTicketViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True
    pagination_class = None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        err = require_platform_cap(request.user, "tickets")
        if err:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(err[0]["detail"])

    def get_queryset(self):
        qs = SupportTicket.objects.select_related(
            "organization", "assignee", "created_by"
        ).prefetch_related("messages")
        st = self.request.query_params.get("status")
        cat = self.request.query_params.get("category")
        if st:
            qs = qs.filter(status=st)
        if cat:
            qs = qs.filter(category=cat)
        return qs.order_by("-updated_at")

    def create(self, request, *args, **kwargs):
        org = Organization.objects.filter(pk=request.data.get("organization")).first()
        if not org:
            return Response({"detail": "organization required"}, status=400)
        subject = (request.data.get("subject") or "").strip()
        body = (request.data.get("body") or "").strip()
        if not subject:
            return Response({"detail": "subject required"}, status=400)
        ticket = SupportTicket.objects.create(
            organization=org,
            ticket_no=_ticket_no(),
            subject=subject[:200],
            category=request.data.get("category") or SupportTicket.Category.GENERAL,
            priority=request.data.get("priority") or SupportTicket.Priority.NORMAL,
            created_by=request.user,
            assignee=request.user,
            last_message_at=timezone.now(),
        )
        if body:
            SupportTicketMessage.objects.create(
                ticket=ticket,
                author=request.user,
                body=body,
                is_from_platform=True,
                is_internal=bool(request.data.get("is_internal")),
            )
        return Response(SupportTicketSerializer(ticket).data, status=201)

    def partial_update(self, request, *args, **kwargs):
        ticket = self.get_object()
        for field in ("status", "priority", "category"):
            if field in request.data:
                setattr(ticket, field, request.data[field])
        if "assignee" in request.data and has_platform_cap(request.user, "tickets.assign"):
            aid = request.data.get("assignee")
            ticket.assignee = User.objects.filter(pk=aid).first() if aid else None
        ticket.save()
        return Response(SupportTicketSerializer(ticket).data)

    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"detail": "body required"}, status=400)
        internal = bool(request.data.get("is_internal"))
        msg = SupportTicketMessage.objects.create(
            ticket=ticket,
            author=request.user,
            body=body,
            is_from_platform=True,
            is_internal=internal,
        )
        ticket.last_message_at = timezone.now()
        if not internal:
            ticket.status = SupportTicket.Status.WAITING
        elif ticket.status == SupportTicket.Status.OPEN:
            ticket.status = SupportTicket.Status.IN_PROGRESS
        ticket.save(update_fields=["last_message_at", "status", "updated_at"])
        return Response(SupportTicketMessageSerializer(msg).data, status=201)


class PlatformStaffViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
    serializer_class = PlatformStaffSerializer
    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True
    pagination_class = None
    queryset = PlatformStaff.objects.select_related("user").all()
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "title",
        "notes",
    )
    filterset_fields = ("role", "is_active")
    ordering_fields = ("role", "is_active", "created_at", "user__username")

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        err = require_platform_cap(request.user, "staff")
        if err:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(err[0]["detail"])

    def create(self, request, *args, **kwargs):
        username = (request.data.get("username") or "").strip()
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
        role = request.data.get("role") or PlatformStaff.Role.SUPPORT
        if role not in ROLE_CAPS or role == "owner":
            # owner is is_superuser only
            if role != "owner":
                return Response({"detail": "Invalid role"}, status=400)
            return Response(
                {"detail": "Owner role is reserved for Django superuser"}, status=400
            )
        user = None
        if username:
            user = User.objects.filter(username=username).first()
        if not user and email:
            user = User.objects.filter(email=email).first()
        if not user:
            if not username or not password:
                return Response(
                    {"detail": "username + password required to create staff user"},
                    status=400,
                )
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=request.data.get("first_name") or "",
                last_name=request.data.get("last_name") or "",
                is_staff=True,
            )
            from accounts.models import UserProfile

            UserProfile.objects.get_or_create(
                user=user, defaults={"organization": None, "role": "viewer"}
            )
        else:
            user.is_staff = True
            if email:
                user.email = email
            user.save()
        staff, _ = PlatformStaff.objects.update_or_create(
            user=user,
            defaults={
                "role": role,
                "is_active": True,
                "title": request.data.get("title") or "",
                "notes": request.data.get("notes") or "",
            },
        )
        return Response(PlatformStaffSerializer(staff).data, status=201)


class PlatformExtendTenantView(APIView):
    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True

    def post(self, request):
        err = require_platform_cap(request.user, "tenants.extend")
        if err:
            return Response(err[0], status=err[1])
        org = Organization.objects.filter(pk=request.data.get("id")).first()
        if not org:
            return Response({"detail": "Tenant not found"}, status=404)
        days = int(request.data.get("days") or 14)
        as_trial = request.data.get("as_trial")
        if as_trial is not None:
            as_trial = bool(as_trial)
        extend_subscription(org, days, as_trial=as_trial)
        return Response(
            {
                "ok": True,
                "id": org.id,
                "trial_ends": org.trial_ends,
                "subscription_ends": org.subscription_ends,
                "plan": org.plan,
                "plan_status": org.plan_status,
            }
        )


class PlatformMeCapsView(APIView):
    permission_classes = [IsAuthenticated]
    rbac_exempt = True
    subscription_exempt = True

    def get(self, request):
        return Response(
            {
                "is_platform_user": is_platform_user(request.user),
                "platform_role": platform_role(request.user),
                "platform_capabilities": platform_capabilities(request.user),
                "role_catalog": ROLE_CAPS,
            }
        )
