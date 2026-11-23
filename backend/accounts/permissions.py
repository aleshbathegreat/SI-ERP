from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.rbac import can
from core.access import subscription_open, user_organization


METHOD_ACTION = {
    "GET": "view",
    "HEAD": "view",
    "OPTIONS": "view",
    "POST": "add",
    "PUT": "change",
    "PATCH": "change",
    "DELETE": "delete",
}


class HasOpenSubscription(BasePermission):
    message = "Subscription ended. Renew on Billing to reopen the ERP."

    def has_permission(self, request, view):
        if getattr(view, "subscription_exempt", False):
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        from core.platform_rbac import is_platform_user

        if is_platform_user(request.user):
            return True
        org = user_organization(request.user)
        if org is None:
            return True
        if subscription_open(org):
            return True
        from core.access import subscription_closed_message

        self.message = subscription_closed_message(org)
        return False


class HasModulePermission(BasePermission):
    """
    Enforce tenant RBAC using view.rbac_module.
    Optional view.rbac_action overrides HTTP→action mapping.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        if getattr(view, "rbac_exempt", False):
            return True
        if not request.user or not request.user.is_authenticated:
            return False

        module = getattr(view, "rbac_module", None)
        if not module:
            # No module declared → allow (subscription still applies)
            return True

        action = getattr(view, "rbac_action", None) or METHOD_ACTION.get(
            request.method.upper(), "view"
        )

        # Bulk delete is a delete action. Approve/reject are review actions
        # (approver roles have change, not add) even though they are POST.
        action_name = getattr(view, "action", None)
        if action_name == "bulk_delete":
            action = "delete"
        elif action_name in ("approve", "reject", "move", "complete"):
            action = "change"

        if can(request.user, module, action):
            return True

        # Owner entitlement is already applied inside can() via package modules.
        self.message = f"Missing permission: {module}:{action}"
        return False
