from rest_framework import viewsets

from contracts.models import Contract
from contracts.serializers import ContractSerializer
from core.bulk import BulkDeleteMixin
from core.scoping import OrgScopedQuerysetMixin


class ContractViewSet(BulkDeleteMixin, OrgScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Contract.objects.select_related("customer", "vendor")
    serializer_class = ContractSerializer
    search_fields = ("contract_no", "title", "party_name")
    filterset_fields = ("status", "customer", "vendor")
    rbac_module = "contracts.contracts"
