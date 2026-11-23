from django.db.models.deletion import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.exceptions import friendly_protect_message
from core.softdelete import SoftDeleteDestroyMixin, soft_delete_instance


class BulkDeleteMixin(SoftDeleteDestroyMixin):
    """Enterprise bulk soft-delete for ModelViewSets."""

    @action(detail=False, methods=["post"], url_path="bulk-delete")
    def bulk_delete(self, request):
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "ids must be a non-empty list"}, status=400)
        qs = self.get_queryset().filter(pk__in=ids)
        rows = list(qs)
        count = 0
        try:
            for row in rows:
                if hasattr(row, "is_deleted"):
                    soft_delete_instance(row, user=request.user)
                else:
                    row.delete()
                count += 1
        except (ProtectedError, RestrictedError) as exc:
            return Response(
                {"detail": friendly_protect_message(exc), "code": "protected"},
                status=status.HTTP_409_CONFLICT,
            )
        return Response({"deleted": count}, status=status.HTTP_200_OK)
