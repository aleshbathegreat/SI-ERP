from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from accounts.mfa import MfaDisableView, MfaSetupView
from accounts.password_reset import PasswordResetConfirmView, PasswordResetRequestView
from accounts.views import DashboardStatsView, LoginView, MeView
from accounts.rbac_views import (
    EnsureRolesView,
    ModuleCatalogView,
    RoleViewSet,
    TenantUserViewSet,
)
from config.auth_urls_fix import OpenTokenRefreshView
from core.approvals import ApprovalsInboxView
from core.audit_views import AuditLogViewSet
from core.email_views import (
    EmailTemplateViewSet,
    MailMessageViewSet,
    PlatformSmtpView,
    TenantEmailProfileViewSet,
    TenantSmtpView,
)
from ops.views import (
    CustomerContractViewSet,
    CustomerViewSet,
    DeliveryNoteViewSet,
    GoodsReceiptViewSet,
    ItemLotViewSet,
    ItemViewSet,
    UnitOfMeasureViewSet,
    LandedCostViewSet,
    LotBatchViewSet,
    PriceListViewSet,
    PurchaseOrderViewSet,
    PurchaseRequisitionViewSet,
    PurchaseReturnViewSet,
    SalesOrderViewSet,
    SalesQuotationViewSet,
    SalesReturnViewSet,
    SerialNumberViewSet,
    StockLevelViewSet,
    StockMovementViewSet,
    StocktakeViewSet,
    VendorRFQQuoteViewSet,
    VendorRFQViewSet,
    WarehouseViewSet,
)
from mfg.views import BomLineViewSet, BomViewSet, WorkOrderViewSet
from contracts.views import ContractViewSet
from core.billing_payfast import (
    BillingCheckoutView,
    PlatformPayFastView,
    TenantPayGatewayView,
    payfast_return,
)
from core.platform_views import (
    PlatformModuleCatalogView,
    PlatformOverviewView,
    PlatformPackageViewSet,
    PlatformTenantsView,
)
from core.saas_ops_views import (
    PlatformExtendTenantView,
    PlatformInvoiceViewSet,
    PlatformMeCapsView,
    PlatformStaffViewSet,
    PlatformTicketViewSet,
    TenantInvoiceViewSet,
    TenantTicketViewSet,
)
from core.notification_views import NotificationMarkReadView, NotificationsInboxView
from core.domain_views import (
    PlatformDomainConfigView,
    ResolveHostView,
    TenantDomainVerifyView,
    TenantDomainView,
)
from core.doc_views import NextDocNoView
from core.ops_views import BackupView, HealthView, OpsStatusView
from core.views import BillingStatusView, PlansView, RenewSubscriptionView, SignupView
from finance.report_views import (
    FinanceReportRunView,
    SavedReportViewSet,
    TaxReturnViewSet,
)
from finance.production_views import (
    AccountingPeriodViewSet,
    AnnualTaxCertificateView,
    BankStatementLineViewSet,
    PayrollBankFileView,
    TaxChallanViewSet,
)
from crm.views import ActivityViewSet, LeadViewSet, OpportunityViewSet
from dms.views import (
    DocumentFolderViewSet,
    DocumentTypeViewSet,
    DocumentViewSet,
    MetadataTypeViewSet,
    TagViewSet,
)
from chat.views import (
    ChatDirectView,
    ChatMemberView,
    ChatMessageDetailView,
    ChatMessagesView,
    ChatPeopleView,
    ChatRoomDetailView,
    ChatRoomsView,
)
from comments.views import RecordCommentViewSet
from notifications.views import InboxMessageViewSet
from tasks.views import WorkTaskViewSet
from dms.workflow_views import (
    WorkflowActionViewSet,
    WorkflowCaseViewSet,
    WorkflowDefinitionViewSet,
    WorkflowStateViewSet,
    WorkflowTransitionEventViewSet,
    WorkflowTransitionFieldViewSet,
    WorkflowTransitionViewSet,
    WorkflowTriggerViewSet,
)
from ops.wms_views import PickListViewSet, WarehouseBinViewSet
from finance.views import (
    AccountTypeViewSet,
    AccountViewSet,
    AssetRepairViewSet,
    BankAccountViewSet,
    BankReconciliationViewSet,
    BudgetViewSet,
    AssetDepreciationLineViewSet,
    AssetDepreciationRunViewSet,
    ChequeRegisterViewSet,
    CostCenterViewSet,
    CurrencyViewSet,
    CustomerInvoiceViewSet,
    EInvoiceSubmissionViewSet,
    FbrInvoiceSubmissionViewSet,
    FinanceReportsView,
    FixedAssetViewSet,
    FxRateViewSet,
    IntercompanyPartnerViewSet,
    IntercompanyTxnViewSet,
    InvestmentViewSet,
    JournalEntryViewSet,
    MaintenanceWorkOrderViewSet,
    PmScheduleViewSet,
    TaxCodeViewSet,
    VendorInvoiceViewSet,
    VendorViewSet,
)
from service.views import ServiceCaseViewSet, ServiceNoteViewSet
from qms.views import CapaViewSet, NcrViewSet, QualityInspectionViewSet
from projects.views import (
    ProjectCostViewSet,
    ProjectTaskViewSet,
    ProjectViewSet,
    TimeEntryViewSet,
)
from ess.views import (
    EssAttendanceRegularizeView,
    EssAttendanceView,
    EssClaimsView,
    EssDashboardView,
    EssDocumentsView,
    EssLeaveBalancesView,
    EssLeaveTypesView,
    EssLeavesView,
    EssPayslipPrintView,
    EssPayslipsView,
    EssTaxCertificateView,
    EssProfileView,
    EssTasksView,
    EssTaskRemindView,
    EssPerformanceView,
    EssActivityView,
    EssPunchView,
)
from core.tier4_views import (
    ApprovalMatrixRuleViewSet,
    DocNumberSeriesViewSet,
    ImportHubCatalogView,
    ImportHubCommitView,
    ImportHubPackCommitView,
    ImportHubPackPreviewView,
    ImportHubPreviewView,
    ImportHubTemplateView,
    ImportHubTemplatesPackView,
)
from integrations.views import (
    IntegrationCatalogView,
    IntegrationConnectionViewSet,
    IntegrationEnsureDefaultsView,
    IntegrationTestView,
)
from hr.integrations import (
    AttendanceDeviceCatalogView,
    AttendanceDeviceSyncView,
    AttendanceDeviceViewSet,
)
from hr.views import (
    AttendanceHolidayViewSet,
    AttendanceRecordViewSet,
    AttendanceRegularizationViewSet,
    BenefitPlanViewSet,
    DepartmentViewSet,
    DesignationViewSet,
    DocumentTypeDefinitionViewSet,
    EmployeeBenefitViewSet,
    EmployeeDocumentViewSet,
    EmployeeViewSet,
    ExpenseClaimViewSet,
    FinalSettlementViewSet,
    JobHistoryViewSet,
    LeaveBalanceViewSet,
    LeaveRequestViewSet,
    LeaveTypeViewSet,
    OvertimePolicyViewSet,
    PerformanceReviewViewSet,
    ProbationRecordViewSet,
    RecruitmentRequestViewSet,
    SeparationRecordViewSet,
    ShiftViewSet,
    TrainingCourseViewSet,
    TrainingRecordViewSet,
)
from payroll.views import (
    EmployeeLoanViewSet,
    LoanRepaymentViewSet,
    PayrollPeriodViewSet,
    PayslipViewSet,
    SalaryStructureViewSet,
)

router = DefaultRouter()
router.register(r"finance/accounts", AccountViewSet)
router.register(r"finance/account-types", AccountTypeViewSet)
router.register(r"finance/cost-centers", CostCenterViewSet)
router.register(r"finance/vendors", VendorViewSet)
router.register(r"finance/journals", JournalEntryViewSet)
router.register(r"finance/budgets", BudgetViewSet)
router.register(r"finance/invoices", VendorInvoiceViewSet)
router.register(r"finance/banks", BankAccountViewSet)
router.register(r"finance/bank-reconciliations", BankReconciliationViewSet)
router.register(r"finance/bank-statements", BankStatementLineViewSet)
router.register(r"finance/investments", InvestmentViewSet)
router.register(r"finance/assets", FixedAssetViewSet)
router.register(r"finance/asset-repairs", AssetRepairViewSet)
router.register(r"finance/maintenance-orders", MaintenanceWorkOrderViewSet)
router.register(r"finance/pm-schedules", PmScheduleViewSet)
router.register(r"service/cases", ServiceCaseViewSet)
router.register(r"service/notes", ServiceNoteViewSet)
router.register(r"qms/inspections", QualityInspectionViewSet)
router.register(r"qms/ncrs", NcrViewSet)
router.register(r"qms/capas", CapaViewSet)
router.register(r"finance/tax-codes", TaxCodeViewSet)
router.register(r"finance/tax-challans", TaxChallanViewSet)
router.register(r"finance/tax-returns", TaxReturnViewSet)
router.register(r"finance/saved-reports", SavedReportViewSet)
router.register(r"finance/periods", AccountingPeriodViewSet)
router.register(r"finance/currencies", CurrencyViewSet)
router.register(r"finance/fx-rates", FxRateViewSet)
router.register(r"finance/cheques", ChequeRegisterViewSet)
router.register(r"finance/intercompany", IntercompanyPartnerViewSet)
router.register(r"finance/intercompany-txns", IntercompanyTxnViewSet)
router.register(r"crm/leads", LeadViewSet)
router.register(r"crm/opportunities", OpportunityViewSet)
router.register(r"crm/activities", ActivityViewSet)
router.register(r"projects/projects", ProjectViewSet)
router.register(r"projects/tasks", ProjectTaskViewSet)
router.register(r"projects/costs", ProjectCostViewSet)
router.register(r"projects/timesheets", TimeEntryViewSet)
router.register(r"hr/departments", DepartmentViewSet)
router.register(r"hr/designations", DesignationViewSet)
router.register(r"hr/shifts", ShiftViewSet)
router.register(r"hr/overtime-policies", OvertimePolicyViewSet)
router.register(r"hr/employees", EmployeeViewSet)
router.register(r"hr/leave-types", LeaveTypeViewSet)
router.register(r"hr/leave-balances", LeaveBalanceViewSet)
router.register(r"hr/leave-requests", LeaveRequestViewSet)
router.register(r"hr/recruitment", RecruitmentRequestViewSet)
router.register(r"hr/benefit-plans", BenefitPlanViewSet)
router.register(r"hr/employee-benefits", EmployeeBenefitViewSet)
router.register(r"hr/attendance", AttendanceRecordViewSet)
router.register(r"hr/attendance-regularizations", AttendanceRegularizationViewSet)
router.register(r"hr/attendance-holidays", AttendanceHolidayViewSet)
router.register(r"hr/attendance-devices", AttendanceDeviceViewSet)
router.register(r"hr/probation", ProbationRecordViewSet)
router.register(r"hr/performance", PerformanceReviewViewSet)
router.register(r"hr/training-courses", TrainingCourseViewSet)
router.register(r"hr/training", TrainingRecordViewSet)
router.register(r"hr/separations", SeparationRecordViewSet)
router.register(r"hr/settlements", FinalSettlementViewSet)
router.register(r"hr/claims", ExpenseClaimViewSet)
router.register(r"hr/document-types", DocumentTypeDefinitionViewSet)
router.register(r"hr/documents", EmployeeDocumentViewSet)
router.register(r"hr/job-history", JobHistoryViewSet)
router.register(r"payroll/structures", SalaryStructureViewSet)
router.register(r"payroll/periods", PayrollPeriodViewSet)
router.register(r"payroll/payslips", PayslipViewSet)
router.register(r"payroll/loans", EmployeeLoanViewSet)
router.register(r"payroll/loan-repayments", LoanRepaymentViewSet)
router.register(r"platform/packages", PlatformPackageViewSet, basename="platform-packages")
router.register(r"platform/invoices", PlatformInvoiceViewSet, basename="platform-invoices")
router.register(r"platform/tickets", PlatformTicketViewSet, basename="platform-tickets")
router.register(r"platform/staff", PlatformStaffViewSet, basename="platform-staff")
router.register(r"saas/invoices", TenantInvoiceViewSet, basename="saas-invoices")
router.register(r"support/tickets", TenantTicketViewSet, basename="support-tickets")
router.register(r"settings/roles", RoleViewSet)
router.register(r"settings/users", TenantUserViewSet, basename="tenant-users")
router.register(r"settings/email-profiles", TenantEmailProfileViewSet)
router.register(r"settings/mail-messages", MailMessageViewSet, basename="mail-messages")
router.register(r"settings/email-templates", EmailTemplateViewSet)
router.register(r"settings/audit", AuditLogViewSet, basename="audit-logs")
router.register(r"settings/doc-series", DocNumberSeriesViewSet)
router.register(r"settings/approval-matrix", ApprovalMatrixRuleViewSet)
router.register(
    r"settings/integrations/connections",
    IntegrationConnectionViewSet,
    basename="integration-connections",
)
router.register(r"sales/customers", CustomerViewSet)
router.register(r"sales/quotes", SalesQuotationViewSet)
router.register(r"sales/orders", SalesOrderViewSet)
router.register(r"sales/deliveries", DeliveryNoteViewSet)
router.register(r"sales/returns", SalesReturnViewSet)
router.register(r"sales/pricing", PriceListViewSet)
router.register(r"sales/invoices", CustomerInvoiceViewSet)
router.register(r"inventory/warehouses", WarehouseViewSet)
router.register(r"inventory/bins", WarehouseBinViewSet)
router.register(r"inventory/pick-lists", PickListViewSet)
router.register(r"dms/folders", DocumentFolderViewSet)
router.register(r"dms/types", DocumentTypeViewSet)
router.register(r"dms/tags", TagViewSet)
router.register(r"dms/metadata-types", MetadataTypeViewSet)
router.register(r"dms/documents", DocumentViewSet)
router.register(r"dms/workflows", WorkflowDefinitionViewSet)
router.register(r"dms/workflow-states", WorkflowStateViewSet)
router.register(r"dms/workflow-transitions", WorkflowTransitionViewSet)
router.register(r"dms/workflow-transition-events", WorkflowTransitionEventViewSet)
router.register(r"dms/workflow-transition-fields", WorkflowTransitionFieldViewSet)
router.register(r"dms/workflow-triggers", WorkflowTriggerViewSet)
router.register(r"dms/workflow-actions", WorkflowActionViewSet)
router.register(r"dms/workflow-cases", WorkflowCaseViewSet)
router.register(r"inbox", InboxMessageViewSet, basename="inbox")
router.register(r"comments", RecordCommentViewSet, basename="comments")
router.register(r"work-tasks", WorkTaskViewSet, basename="work-tasks")
router.register(r"inventory/items", ItemViewSet)
router.register(r"inventory/units", UnitOfMeasureViewSet)
router.register(r"inventory/stock-levels", StockLevelViewSet, basename="stock-levels")
router.register(r"inventory/movements", StockMovementViewSet)
router.register(r"inventory/stocktakes", StocktakeViewSet)
router.register(r"inventory/batches", LotBatchViewSet)
router.register(r"inventory/lots", ItemLotViewSet)
router.register(r"inventory/serials", SerialNumberViewSet)
router.register(r"procurement/requisitions", PurchaseRequisitionViewSet)
router.register(r"procurement/rfqs", VendorRFQViewSet)
router.register(r"procurement/rfq-quotes", VendorRFQQuoteViewSet)
router.register(r"procurement/orders", PurchaseOrderViewSet)
router.register(r"procurement/receipts", GoodsReceiptViewSet)
router.register(r"procurement/returns", PurchaseReturnViewSet)
router.register(r"procurement/landed-costs", LandedCostViewSet)
router.register(r"mfg/boms", BomViewSet)
router.register(r"mfg/bom-lines", BomLineViewSet)
router.register(r"mfg/work-orders", WorkOrderViewSet)
router.register(r"sales/contracts", CustomerContractViewSet)
router.register(r"contracts", ContractViewSet)
router.register(r"finance/asset-depreciation", AssetDepreciationRunViewSet)
router.register(
    r"finance/asset-depreciation-lines",
    AssetDepreciationLineViewSet,
    basename="asset-depreciation-lines",
)
router.register(r"finance/e-invoices", EInvoiceSubmissionViewSet)
router.register(
    r"finance/fbr-submissions",
    FbrInvoiceSubmissionViewSet,
    basename="fbr-submissions",
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/public/resolve-host/", ResolveHostView.as_view(), name="resolve_host"),
    path("api/settings/domain/", TenantDomainView.as_view(), name="tenant_domain"),
    path(
        "api/settings/domain/verify/",
        TenantDomainVerifyView.as_view(),
        name="tenant_domain_verify",
    ),
    path(
        "api/platform/domains/",
        PlatformDomainConfigView.as_view(),
        name="platform_domains",
    ),
    path(
        "api/platform/overview/",
        PlatformOverviewView.as_view(),
        name="platform_overview",
    ),
    path(
        "api/platform/module-catalog/",
        PlatformModuleCatalogView.as_view(),
        name="platform_module_catalog",
    ),
    path(
        "api/platform/tenants/",
        PlatformTenantsView.as_view(),
        name="platform_tenants",
    ),
    path(
        "api/platform/tenants/extend/",
        PlatformExtendTenantView.as_view(),
        name="platform_tenants_extend",
    ),
    path(
        "api/platform/me/",
        PlatformMeCapsView.as_view(),
        name="platform_me",
    ),

    path(
        "api/chat/people/",
        ChatPeopleView.as_view(),
        name="chat_people",
    ),
    path("api/chat/rooms/", ChatRoomsView.as_view(), name="chat_rooms"),
    path("api/chat/direct/", ChatDirectView.as_view(), name="chat_direct"),
    path(
        "api/chat/rooms/<int:room_id>/messages/",
        ChatMessagesView.as_view(),
        name="chat_messages",
    ),
    path(
        "api/chat/rooms/<int:room_id>/members/<int:user_id>/<str:action>/",
        ChatMemberView.as_view(),
        name="chat_member",
    ),
    path(
        "api/chat/rooms/<int:room_id>/<str:action>/",
        ChatRoomDetailView.as_view(),
        name="chat_room_action",
    ),
    path("api/chat/rooms/<int:room_id>/", ChatRoomDetailView.as_view(), name="chat_room"),
    path(
        "api/chat/messages/<int:message_id>/",
        ChatMessageDetailView.as_view(),
        name="chat_message",
    ),
    path(
        "api/chat/messages/<int:message_id>/remove/",
        ChatMessageDetailView.as_view(),
        name="chat_message_remove",
    ),
    path(
        "api/notifications/",
        NotificationsInboxView.as_view(),
        name="notifications_inbox",
    ),
    path(
        "api/notifications/mark-read/",
        NotificationMarkReadView.as_view(),
        name="notifications_mark_read",
    ),
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path(
        "api/auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "api/auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("api/auth/refresh/", OpenTokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/auth/mfa/setup/", MfaSetupView.as_view(), name="mfa_setup"),
    path("api/auth/mfa/disable/", MfaDisableView.as_view(), name="mfa_disable"),
    path("api/dashboard/", DashboardStatsView.as_view(), name="dashboard"),
    path("api/ops/status/", OpsStatusView.as_view(), name="ops_status"),
    path("api/ops/backup/", BackupView.as_view(), name="backup"),
    path("api/platform/smtp/", PlatformSmtpView.as_view(), name="platform_smtp"),
    path("api/platform/payfast/", PlatformPayFastView.as_view(), name="platform_payfast"),
    path("api/settings/smtp/", TenantSmtpView.as_view(), name="tenant_smtp"),
    path(
        "api/settings/pay-gateway/",
        TenantPayGatewayView.as_view(),
        name="tenant_pay_gateway",
    ),
    path("api/saas/plans/", PlansView.as_view(), name="plans"),
    path("api/saas/signup/", SignupView.as_view(), name="signup"),
    path("api/saas/billing/", BillingStatusView.as_view(), name="billing"),
    path("api/saas/billing/renew/", RenewSubscriptionView.as_view(), name="billing_renew"),
    path(
        "api/saas/billing/checkout/",
        BillingCheckoutView.as_view(),
        name="billing_checkout",
    ),
    path(
        "api/saas/billing/payfast/return/",
        payfast_return,
        name="payfast_return",
    ),
    path("api/settings/modules/", ModuleCatalogView.as_view(), name="module_catalog"),
    path("api/settings/roles/ensure/", EnsureRolesView.as_view(), name="ensure_roles"),
    path("api/finance/reports/", FinanceReportsView.as_view(), name="finance_reports"),
    path(
        "api/finance/reports/run/",
        FinanceReportRunView.as_view(),
        name="finance_reports_run",
    ),
    path("api/docs/next-number/", NextDocNoView.as_view(), name="next_doc_number"),
    path("api/payroll/bank-file/", PayrollBankFileView.as_view(), name="payroll_bank_file"),
    path(
        "api/payroll/tax-certificate/",
        AnnualTaxCertificateView.as_view(),
        name="annual_tax_certificate",
    ),
    path("api/approvals/inbox/", ApprovalsInboxView.as_view(), name="approvals_inbox"),
    path(
        "api/hr/attendance/device-sync/",
        AttendanceDeviceSyncView.as_view(),
        name="attendance_device_sync",
    ),
    path(
        "api/hr/attendance/connectors/",
        AttendanceDeviceCatalogView.as_view(),
        name="attendance_connectors_catalog",
    ),
    path("api/ess/dashboard/", EssDashboardView.as_view(), name="ess_dashboard"),
    path("api/ess/profile/", EssProfileView.as_view(), name="ess_profile"),
    path("api/ess/performance/", EssPerformanceView.as_view(), name="ess_performance"),
    path("api/ess/activity/", EssActivityView.as_view(), name="ess_activity"),
    path("api/ess/tasks/", EssTasksView.as_view(), name="ess_tasks"),
    path("api/ess/tasks/<int:pk>/remind/", EssTaskRemindView.as_view(), name="ess_task_remind"),
    path("api/ess/leave-types/", EssLeaveTypesView.as_view(), name="ess_leave_types"),
    path("api/ess/leave-balances/", EssLeaveBalancesView.as_view(), name="ess_leave_balances"),
    path("api/ess/leaves/", EssLeavesView.as_view(), name="ess_leaves"),
    path("api/ess/attendance/", EssAttendanceView.as_view(), name="ess_attendance"),
    path(
        "api/ess/attendance/regularize/",
        EssAttendanceRegularizeView.as_view(),
        name="ess_attendance_regularize",
    ),
    path("api/ess/attendance/punch/", EssPunchView.as_view(), name="ess_punch"),
    path("api/ess/payslips/", EssPayslipsView.as_view(), name="ess_payslips"),
    path(
        "api/ess/payslips/tax-certificate/",
        EssTaxCertificateView.as_view(),
        name="ess_tax_certificate",
    ),
    path(
        "api/ess/payslips/<int:pk>/print/",
        EssPayslipPrintView.as_view(),
        name="ess_payslip_print",
    ),
    path("api/ess/documents/", EssDocumentsView.as_view(), name="ess_documents"),
    path("api/ess/claims/", EssClaimsView.as_view(), name="ess_claims"),
    path(
        "api/settings/import-hub/catalog/",
        ImportHubCatalogView.as_view(),
        name="import_hub_catalog",
    ),
    path(
        "api/settings/import-hub/templates-pack/",
        ImportHubTemplatesPackView.as_view(),
        name="import_hub_templates_pack",
    ),
    path(
        "api/settings/import-hub/templates/<str:entity>/",
        ImportHubTemplateView.as_view(),
        name="import_hub_template",
    ),
    path(
        "api/settings/import-hub/preview/",
        ImportHubPreviewView.as_view(),
        name="import_hub_preview",
    ),
    path(
        "api/settings/import-hub/commit/",
        ImportHubCommitView.as_view(),
        name="import_hub_commit",
    ),
    path(
        "api/settings/import-hub/preview-pack/",
        ImportHubPackPreviewView.as_view(),
        name="import_hub_preview_pack",
    ),
    path(
        "api/settings/import-hub/commit-pack/",
        ImportHubPackCommitView.as_view(),
        name="import_hub_commit_pack",
    ),
    path(
        "api/settings/integrations/catalog/",
        IntegrationCatalogView.as_view(),
        name="integrations_catalog",
    ),
    path(
        "api/settings/integrations/ensure-defaults/",
        IntegrationEnsureDefaultsView.as_view(),
        name="integrations_ensure_defaults",
    ),
    path(
        "api/settings/integrations/connections/<int:pk>/test/",
        IntegrationTestView.as_view(),
        name="integrations_test",
    ),
    path("api/", include(router.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
]

# Tenant branding logos / favicons (volume jmc_media) — always served (prod + debug)
from django.urls import re_path
from django.views.static import serve as media_serve

urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        media_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
