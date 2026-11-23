"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  AppBar,
  Box,
  Chip,
  Collapse,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Tooltip,
  Typography,
  Button,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PeopleIcon from "@mui/icons-material/People";
import EventAvailableIcon from "@mui/icons-material/EventAvailable";
import CalendarMonthOutlinedIcon from "@mui/icons-material/CalendarMonthOutlined";
import CategoryIcon from "@mui/icons-material/Category";
import LocalOfferOutlinedIcon from "@mui/icons-material/LocalOfferOutlined";
import TuneIcon from "@mui/icons-material/Tune";
import BadgeIcon from "@mui/icons-material/Badge";
import BeachAccessIcon from "@mui/icons-material/BeachAccess";
import AccountBalanceIcon from "@mui/icons-material/AccountBalance";
import PaymentsIcon from "@mui/icons-material/Payments";
import StoreIcon from "@mui/icons-material/Store";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import SchemaIcon from "@mui/icons-material/Schema";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import CreditCardIcon from "@mui/icons-material/CreditCard";
import SecurityIcon from "@mui/icons-material/Security";
import ManageAccountsIcon from "@mui/icons-material/ManageAccounts";
import LogoutIcon from "@mui/icons-material/Logout";
import SavingsIcon from "@mui/icons-material/Savings";
import ScheduleIcon from "@mui/icons-material/Schedule";
import RequestQuoteIcon from "@mui/icons-material/RequestQuote";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import DomainIcon from "@mui/icons-material/Domain";
import PercentIcon from "@mui/icons-material/Percent";
import AssessmentIcon from "@mui/icons-material/Assessment";
import WorkIcon from "@mui/icons-material/Work";
import HealthAndSafetyIcon from "@mui/icons-material/HealthAndSafety";
import FingerprintIcon from "@mui/icons-material/Fingerprint";
import FactCheckIcon from "@mui/icons-material/FactCheck";
import PersonOutlineIcon from "@mui/icons-material/PersonOutlined";
import HistoryIcon from "@mui/icons-material/History";
import ApprovalIcon from "@mui/icons-material/Approval";
import EmailIcon from "@mui/icons-material/Email";
import InventoryIcon from "@mui/icons-material/Inventory2";
import LocalShippingIcon from "@mui/icons-material/LocalShipping";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import PointOfSaleIcon from "@mui/icons-material/PointOfSale";
import BusinessIcon from "@mui/icons-material/Business";
import DnsIcon from "@mui/icons-material/Dns";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import HelpOutlineIcon from "@mui/icons-material/HelpOutlineOutlined";
import DescriptionIcon from "@mui/icons-material/Description";
import HubIcon from "@mui/icons-material/Hub";
import SupportAgentIcon from "@mui/icons-material/SupportAgent";
import ChatOutlinedIcon from "@mui/icons-material/ChatOutlined";
import NoteAltOutlinedIcon from "@mui/icons-material/NoteAltOutlined";
import BuildIcon from "@mui/icons-material/Build";
import EventRepeatIcon from "@mui/icons-material/EventRepeat";
import VerifiedOutlinedIcon from "@mui/icons-material/VerifiedOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import TaskAltIcon from "@mui/icons-material/TaskAlt";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import { SETTINGS_GROUPS, tabMatches } from "@/lib/settingsNav";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { logout } from "@/store/auth/slice";
import ThemeToggle from "@/components/ThemeToggle";
import BrandMark from "@/components/BrandMark";
import HeaderNotifications from "@/components/HeaderNotifications";
import { usePermissions } from "@/hooks/usePermissions";
import { usePlatformCaps } from "@/hooks/usePlatformCaps";

const DRAWER_EXPANDED = 288;
const DRAWER_COLLAPSED = 72;
const SIDEBAR_KEY = "sierp.sidebar.collapsed";
const SIDEBAR_SECTIONS_KEY = "sierp.sidebar.sections";

type NavItem = {
  href: string;
  label: string;
  icon: React.ReactNode;
  module: string;
  platformOnly?: boolean;
  platformCap?: string;
  exact?: boolean;
  settingsGroupId?: string;
  activePrefixes?: string[];
};

const platformNavGroup: { title: string; items: NavItem[] } = {
  title: "Platform · SaaS",
  items: [
    {
      href: "/platform",
      label: "Control center",
      icon: <DashboardIcon />,
      module: "dashboard",
      platformOnly: true,
      platformCap: "overview",
      exact: true,
    },
    {
      href: "/platform/packages",
      label: "Subscription packages",
      icon: <InventoryIcon />,
      module: "dashboard",
      platformOnly: true,
      platformCap: "packages",
    },
    {
      href: "/platform/tenants",
      label: "Tenants",
      icon: <BusinessIcon />,
      module: "dashboard",
      platformOnly: true,
      platformCap: "tenants",
    },
    {
      href: "/platform/invoices",
      label: "SaaS invoices",
      icon: <RequestQuoteIcon />,
      module: "dashboard",
      platformOnly: true,
      platformCap: "invoices",
    },
    {
      href: "/platform/tickets",
      label: "Support tickets",
      icon: <ApprovalIcon />,
      module: "dashboard",
      platformOnly: true,
      platformCap: "tickets",
    },
    {
      href: "/platform/staff",
      label: "Platform staff",
      icon: <ManageAccountsIcon />,
      module: "dashboard",
      platformOnly: true,
      platformCap: "staff",
    },
    {
      href: "/platform/domains",
      label: "Domains",
      icon: <DnsIcon />,
      module: "dashboard",
      platformOnly: true,
      platformCap: "domains",
    },
    {
      href: "/settings/platform-smtp",
      label: "Platform SMTP",
      icon: <EmailIcon />,
      module: "dashboard",
      platformOnly: true,
      platformCap: "smtp",
    },
    {
      href: "/settings/platform-payfast",
      label: "Platform PayFast",
      icon: <CreditCardIcon />,
      module: "dashboard",
      platformOnly: true,
      platformCap: "payfast",
    },
  ],
};

const tenantNavGroups: { title: string; items: NavItem[] }[] = [
  {
    title: "Overview",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: <DashboardIcon />, module: "dashboard" },
      { href: "/guide", label: "User guide", icon: <MenuBookIcon />, module: "dashboard" },
      { href: "/approvals", label: "Approvals (LoA)", icon: <ApprovalIcon />, module: "approvals" },
      {
        href: "/ess",
        label: "Employee portal",
        icon: <PersonOutlineIcon />,
        module: "ess",
      },
    ],
  },
  {
    title: "Finance",
    items: [
      { href: "/finance/accounts", label: "Chart of Accounts", icon: <AccountBalanceIcon />, module: "finance.accounts" },
      { href: "/finance/account-types", label: "Account types", icon: <CategoryIcon />, module: "finance.accounts" },
      { href: "/finance/cost-centers", label: "Cost centers", icon: <CategoryIcon />, module: "finance.cost_centers" },
      { href: "/finance/journals", label: "Journal entries", icon: <ReceiptLongIcon />, module: "finance.journals" },
      { href: "/finance/periods", label: "Period close", icon: <ReceiptLongIcon />, module: "finance.journals" },
      { href: "/finance/budgets", label: "Budgets", icon: <SavingsIcon />, module: "finance.budgets" },
      { href: "/finance/vendors", label: "Vendors", icon: <StoreIcon />, module: "finance.vendors" },
      { href: "/finance/invoices", label: "AP invoices & payments", icon: <RequestQuoteIcon />, module: "finance.invoices" },
      { href: "/finance/banks", label: "Bank accounts", icon: <AccountBalanceWalletIcon />, module: "finance.banks" },
      { href: "/finance/reconciliations", label: "Bank reconciliation", icon: <AccountBalanceWalletIcon />, module: "finance.banks" },
      { href: "/finance/treasury", label: "Treasury / investments", icon: <DomainIcon />, module: "finance.treasury" },
      { href: "/finance/assets", label: "Fixed assets", icon: <DomainIcon />, module: "finance.assets" },
      { href: "/finance/asset-depreciation", label: "Asset depreciation", icon: <DomainIcon />, module: "finance.assets" },
      { href: "/finance/currencies", label: "Currencies", icon: <AccountBalanceIcon />, module: "finance.fx" },
      { href: "/finance/fx-rates", label: "FX rates", icon: <AccountBalanceIcon />, module: "finance.fx" },
      { href: "/finance/cheques", label: "Cheques / PDC", icon: <AccountBalanceWalletIcon />, module: "finance.cheques" },
      { href: "/finance/intercompany", label: "IC partners", icon: <HubIcon />, module: "finance.intercompany" },
      { href: "/finance/intercompany-txns", label: "IC transactions", icon: <HubIcon />, module: "finance.intercompany" },
      { href: "/finance/e-invoices", label: "FBR e-invoice", icon: <ReceiptLongIcon />, module: "finance.einvoice" },
      { href: "/finance/tax", label: "Tax codes", icon: <PercentIcon />, module: "finance.tax" },
      { href: "/finance/challans", label: "Tax challans", icon: <PercentIcon />, module: "finance.tax" },
      { href: "/finance/tax-returns", label: "Tax returns", icon: <PercentIcon />, module: "finance.tax_returns" },
      { href: "/finance/reports", label: "Statutory reports", icon: <AssessmentIcon />, module: "finance.reports" },
    ],
  },
  {
    title: "CRM",
    items: [
      { href: "/crm/leads", label: "Leads", icon: <PointOfSaleIcon />, module: "crm.leads" },
      { href: "/crm/opportunities", label: "Opportunities", icon: <RequestQuoteIcon />, module: "crm.opportunities" },
      { href: "/crm/activities", label: "Activities", icon: <FactCheckIcon />, module: "crm.activities" },
      { href: "/crm/calendar", label: "Calendar", icon: <CalendarMonthOutlinedIcon />, module: "crm.activities" },
    ],
  },
  {
    title: "Projects",
    items: [
      { href: "/projects", label: "Projects", icon: <WorkIcon />, module: "projects.projects" },
      { href: "/projects/tasks", label: "Tasks", icon: <FactCheckIcon />, module: "projects.tasks" },
      { href: "/projects/costs", label: "Costs", icon: <SavingsIcon />, module: "projects.costs" },
      { href: "/projects/timesheets", label: "Timesheets", icon: <ScheduleIcon />, module: "projects.timesheets" },
    ],
  },
  {
    title: "Manufacturing",
    items: [
      { href: "/mfg/boms", label: "BOMs", icon: <InventoryIcon />, module: "mfg.bom" },
      { href: "/mfg/work-orders", label: "Work orders", icon: <LocalShippingIcon />, module: "mfg.work_orders" },
    ],
  },
  {
    title: "Contracts",
    items: [
      { href: "/contracts", label: "Contracts", icon: <DescriptionIcon />, module: "contracts.contracts" },
    ],
  },
  {
    title: "Documents",
    items: [
      { href: "/dms/documents", label: "Documents", icon: <DescriptionIcon />, module: "dms.documents" },
      { href: "/dms/workflows", label: "Workflows", icon: <SchemaIcon />, module: "dms.documents" },
      { href: "/dms/folders", label: "Folders", icon: <AccountTreeIcon />, module: "dms.folders" },
      { href: "/dms/types", label: "Types", icon: <CategoryIcon />, module: "dms.documents" },
      { href: "/dms/tags", label: "Tags", icon: <LocalOfferOutlinedIcon />, module: "dms.documents" },
      { href: "/dms/metadata-types", label: "Metadata", icon: <TuneIcon />, module: "dms.documents" },
    ],
  },
  {
    title: "Service",
    items: [
      { href: "/service/cases", label: "Cases", icon: <SupportAgentIcon />, module: "service.cases" },
      { href: "/service/notes", label: "Case notes", icon: <NoteAltOutlinedIcon />, module: "service.notes" },
    ],
  },
  {
    title: "Maintenance",
    items: [
      { href: "/finance/maintenance-orders", label: "Work orders", icon: <BuildIcon />, module: "finance.maintenance" },
      { href: "/finance/pm-schedules", label: "PM schedules", icon: <EventRepeatIcon />, module: "finance.maintenance" },
    ],
  },
  {
    title: "Quality",
    items: [
      { href: "/qms/inspections", label: "Inspections", icon: <VerifiedOutlinedIcon />, module: "qms.inspections" },
      { href: "/qms/ncrs", label: "NCRs", icon: <ReportProblemOutlinedIcon />, module: "qms.ncrs" },
      { href: "/qms/capas", label: "CAPAs", icon: <TaskAltIcon />, module: "qms.capas" },
    ],
  },
  {
    title: "Sales",
    items: [
      { href: "/sales/customers", label: "Customers", icon: <PointOfSaleIcon />, module: "sales.customers" },
      { href: "/sales/quotes", label: "Quotations", icon: <RequestQuoteIcon />, module: "sales.quotes" },
      { href: "/sales/orders", label: "Sales orders", icon: <ShoppingCartIcon />, module: "sales.orders" },
      { href: "/sales/deliveries", label: "Delivery notes", icon: <LocalShippingIcon />, module: "sales.deliveries" },
      { href: "/sales/returns", label: "Returns / RMA", icon: <LocalShippingIcon />, module: "sales.returns" },
      { href: "/sales/pricing", label: "Price lists", icon: <RequestQuoteIcon />, module: "sales.pricing" },
      { href: "/sales/invoices", label: "AR invoices", icon: <ReceiptLongIcon />, module: "sales.invoices" },
      { href: "/sales/contracts", label: "Recurring contracts", icon: <DescriptionIcon />, module: "sales.contracts" },
      { href: "/sales/credit", label: "Credit aging", icon: <AssessmentIcon />, module: "sales.credit" },
    ],
  },
  {
    title: "Inventory",
    items: [
      {
        href: "/inventory/warehouses",
        label: "Warehouses",
        icon: <InventoryIcon />,
        module: "inventory.warehouses",
      },
      { href: "/inventory/items", label: "Items", icon: <InventoryIcon />, module: "inventory.items" },
      { href: "/inventory/units", label: "Units of measure", icon: <InventoryIcon />, module: "inventory.items" },
      { href: "/inventory/stock", label: "Stock levels", icon: <InventoryIcon />, module: "inventory.items" },
      {
        href: "/inventory/movements",
        label: "Stock movements",
        icon: <LocalShippingIcon />,
        module: "inventory.movements",
      },
      { href: "/inventory/stocktakes", label: "Stocktake", icon: <InventoryIcon />, module: "inventory.stocktake" },
      { href: "/inventory/lots", label: "Lots", icon: <InventoryIcon />, module: "inventory.lots" },
      { href: "/inventory/batches", label: "Warehouse batches", icon: <InventoryIcon />, module: "inventory.batches" },
      { href: "/inventory/serials", label: "Serial numbers", icon: <InventoryIcon />, module: "inventory.serials" },
      { href: "/inventory/bins", label: "Bins", icon: <InventoryIcon />, module: "inventory.bins" },
      { href: "/inventory/pick-lists", label: "Pick lists", icon: <FactCheckIcon />, module: "inventory.pick_lists" },
    ],
  },
  {
    title: "Procurement",
    items: [
      { href: "/procurement/requisitions", label: "Requisitions", icon: <RequestQuoteIcon />, module: "procurement.requisitions" },
      { href: "/procurement/rfqs", label: "Vendor RFQ", icon: <RequestQuoteIcon />, module: "procurement.rfq" },
      { href: "/procurement/orders", label: "Purchase orders", icon: <RequestQuoteIcon />, module: "procurement.orders" },
      { href: "/procurement/receipts", label: "Goods receipts", icon: <LocalShippingIcon />, module: "procurement.receipts" },
      { href: "/procurement/returns", label: "Purchase returns", icon: <LocalShippingIcon />, module: "procurement.returns" },
      { href: "/procurement/landed-costs", label: "Landed cost", icon: <RequestQuoteIcon />, module: "procurement.landed_cost" },
      { href: "/finance/vendors", label: "Vendors", icon: <StoreIcon />, module: "finance.vendors" },
      { href: "/finance/invoices", label: "AP invoices", icon: <ReceiptLongIcon />, module: "finance.invoices" },
    ],
  },
  {
    title: "HR",
    items: [
      { href: "/hr/employees", label: "Employees", icon: <PeopleIcon />, module: "hr.employees" },
      { href: "/hr/job-history", label: "Job history", icon: <HistoryIcon />, module: "hr.employees" },
      { href: "/hr/departments", label: "Departments", icon: <AccountTreeIcon />, module: "hr.departments" },
      { href: "/hr/designations", label: "Designations", icon: <BadgeIcon />, module: "hr.designations" },
      { href: "/hr/shifts", label: "Shifts", icon: <FingerprintIcon />, module: "hr.shifts" },
      { href: "/hr/overtime-policies", label: "Overtime policies", icon: <FingerprintIcon />, module: "hr.overtime" },
      { href: "/hr/claims", label: "Expense claims", icon: <ReceiptLongIcon />, module: "hr.claims" },
      { href: "/hr/recruitment", label: "Recruitment", icon: <WorkIcon />, module: "hr.recruitment" },
      { href: "/hr/benefits", label: "Benefits / EOBI", icon: <HealthAndSafetyIcon />, module: "hr.benefits" },
      { href: "/hr/employee-benefits", label: "Benefit enrollments", icon: <HealthAndSafetyIcon />, module: "hr.benefits" },
      { href: "/hr/attendance", label: "Attendance", icon: <FingerprintIcon />, module: "hr.attendance" },
      {
        href: "/hr/attendance?tab=devices",
        label: "Attendance devices",
        icon: <FingerprintIcon />,
        module: "hr.attendance_devices",
      },
      { href: "/hr/leave-types", label: "Leave types", icon: <BeachAccessIcon />, module: "hr.leave_types" },
      { href: "/hr/leave-balances", label: "Leave balances", icon: <EventAvailableIcon />, module: "hr.leaves" },
      { href: "/hr/leaves", label: "Leave requests", icon: <EventAvailableIcon />, module: "hr.leaves" },
      { href: "/hr/probation", label: "Probation", icon: <FactCheckIcon />, module: "hr.probation" },
      { href: "/hr/performance", label: "Performance", icon: <AssessmentIcon />, module: "hr.performance" },
      { href: "/hr/training-courses", label: "Training catalog", icon: <WorkIcon />, module: "hr.training" },
      { href: "/hr/training", label: "Training enrollments", icon: <WorkIcon />, module: "hr.training" },
      { href: "/hr/separations", label: "Separations", icon: <PersonOutlineIcon />, module: "hr.separation" },
      { href: "/hr/settlements", label: "F&F settlements", icon: <PersonOutlineIcon />, module: "hr.separation" },
      { href: "/hr/document-types", label: "Document matrix", icon: <HistoryIcon />, module: "hr.documents" },
      { href: "/hr/documents", label: "Documents vault", icon: <HistoryIcon />, module: "hr.documents" },
    ],
  },
  {
    title: "Payroll",
    items: [
      { href: "/payroll/structures", label: "Salary structures", icon: <FactCheckIcon />, module: "payroll.structures" },
      { href: "/payroll", label: "Periods & Payslips", icon: <PaymentsIcon />, module: "payroll.periods" },
      { href: "/payroll/loans", label: "Employee loans", icon: <CreditCardIcon />, module: "payroll.loans" },
    ],
  },
  {
    title: "SaaS",
    items: [
      { href: "/billing", label: "Billing & invoices", icon: <CreditCardIcon />, module: "billing" },
      { href: "/support", label: "Support tickets", icon: <ApprovalIcon />, module: "dashboard" },
    ],
  },
  {
    title: "Settings",
    items: [
      {
        href: "/settings/roles",
        label: "Access",
        icon: <ManageAccountsIcon />,
        module: "settings.roles",
        settingsGroupId: "access",
      },
      {
        href: "/settings/email",
        label: "Email",
        icon: <EmailIcon />,
        module: "settings.email",
        settingsGroupId: "email",
      },
      {
        href: "/settings/integrations",
        label: "Integrations",
        icon: <HubIcon />,
        module: "settings.integrations",
        settingsGroupId: "integrations",
      },
      {
        href: "/settings/domain",
        label: "Company",
        icon: <DomainIcon />,
        module: "settings.domain",
        settingsGroupId: "company",
      },
    ],
  },
  {
    title: "Governance",
    items: [
      { href: "/dms/workflows", label: "Workflows", icon: <SchemaIcon />, module: "dms.documents" },
      { href: "/chat", label: "Chat", icon: <ChatOutlinedIcon />, module: "chat" },
      { href: "/inbox", label: "Notifications", icon: <NotificationsNoneOutlinedIcon />, module: "dashboard" },
      { href: "/comments", label: "Comments", icon: <NoteAltOutlinedIcon />, module: "dashboard" },
      { href: "/tasks", label: "Tasks", icon: <TaskAltIcon />, module: "dashboard" },
    ],
  },
];

function navSelected(pathname: string, item: NavItem) {
  if (item.exact) return pathname === item.href;
  const prefixes = item.activePrefixes?.length ? item.activePrefixes : [item.href];
  return prefixes.some((href) => tabMatches(pathname, href));
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});
  const pathname = usePathname();
  const router = useRouter();
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const organization = useAppSelector((s) => s.auth.organization);
  const { canView, isOwner } = usePermissions();
  const { isPlatformUser, can: canPlatform, platformRole } = usePlatformCaps();

  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(SIDEBAR_KEY) === "1");
    } catch {
      /* ignore */
    }
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(SIDEBAR_KEY, next ? "1" : "0");
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  const drawerWidth = collapsed ? DRAWER_COLLAPSED : DRAWER_EXPANDED;

  const visibleGroups = useMemo(() => {
    const tenantGroups = tenantNavGroups
      .map((group) => ({
        ...group,
        items: group.items.flatMap((item) => {
          if (item.platformOnly) return [];
          if (item.settingsGroupId) {
            const def = SETTINGS_GROUPS.find((entry) => entry.id === item.settingsGroupId);
            const tabs = (def?.tabs || []).filter((tab) => canView(tab.module));
            if (!tabs.length) return [];
            return [
              {
                ...item,
                href: tabs[0].href,
                module: tabs[0].module,
                activePrefixes: tabs.map((tab) => tab.href),
              },
            ];
          }
          if (canView(item.module)) return [item];
          if (item.module === "payroll.periods" && canView("payroll.payslips")) {
            return [item];
          }
          if (
            (item.href === "/guide" || item.href === "/support") &&
            canView("dashboard")
          ) {
            return [item];
          }
          return [];
        }),
      }))
      .filter((group) => group.items.length > 0);

    if (!isPlatformUser) return tenantGroups;

    const platformGroup = {
      ...platformNavGroup,
      items: platformNavGroup.items.filter(
        (item) =>
          item.platformOnly && (!item.platformCap || canPlatform(item.platformCap))
      ),
    };
    return organization ? [platformGroup, ...tenantGroups] : [platformGroup];
  }, [canView, canPlatform, isPlatformUser, organization]);

  const activeSectionTitle =
    visibleGroups.find((g) => g.items.some((item) => navSelected(pathname, item)))?.title ||
    visibleGroups[0]?.title ||
    "";

  const markedOpen = Object.keys(openSections).filter((key) => openSections[key] === true);
  const openTitle = markedOpen.length === 1 ? markedOpen[0] : activeSectionTitle;

  // Keep the section for the current page open, and close every other section.
  useEffect(() => {
    if (!activeSectionTitle) return;
    setOpenSections((prev) => {
      const marked = Object.keys(prev).filter((key) => prev[key] === true);
      if (marked.length === 1 && marked[0] === activeSectionTitle) return prev;
      const next = { [activeSectionTitle]: true };
      try {
        localStorage.setItem(SIDEBAR_SECTIONS_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, [activeSectionTitle]);

  const toggleSection = (title: string) => {
    setOpenSections((prev) => {
      const marked = Object.keys(prev).filter((key) => prev[key] === true);
      if (marked.length === 1 && marked[0] === title) return prev;
      const next = { [title]: true };
      try {
        localStorage.setItem(SIDEBAR_SECTIONS_KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  const roleLabel = isPlatformUser
    ? `platform · ${platformRole || "staff"}`
    : user?.profile?.primary_role_name ||
      user?.profile?.role ||
      (isOwner ? "tenant owner" : "member");

  const drawer = useMemo(
    () => (
      <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
        <Toolbar
          sx={{
            alignItems: "center",
            gap: 0.5,
            px: collapsed ? 1 : 2,
            justifyContent: collapsed ? "center" : "space-between",
            minHeight: 64,
          }}
        >
          {collapsed ? (
            <Tooltip title="Expand sidebar" placement="right">
              <IconButton onClick={toggleCollapsed} size="small" aria-label="Expand sidebar">
                <BrandMark size="sm" showName={false} showTagline={false} dense />
              </IconButton>
            </Tooltip>
          ) : (
            <>
              <BrandMark size="sm" showTagline dense />
              <Tooltip title="Collapse sidebar" placement="right">
                <IconButton
                  size="small"
                  onClick={toggleCollapsed}
                  sx={{ display: { xs: "none", sm: "inline-flex" }, flexShrink: 0 }}
                  aria-label="Collapse sidebar"
                >
                  <ChevronLeftIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </>
          )}
        </Toolbar>
        <Divider />
        <Box sx={{ flex: 1, overflow: "auto", overflowX: "hidden" }}>
          {visibleGroups.map((group) => {
            const sectionOpen = collapsed || group.title === openTitle;
            return (
              <List key={group.title} dense disablePadding sx={{ mb: 0.5 }}>
                {!collapsed ? (
                  <ListItemButton
                    onClick={() => toggleSection(group.title)}
                    sx={{
                      position: "sticky",
                      top: 0,
                      zIndex: 2,
                      px: 2,
                      py: 0.75,
                      minHeight: 36,
                      bgcolor: "background.paper",
                      backgroundImage: "none",
                      borderBottom: "1px solid",
                      borderColor: "divider",
                      "&:hover": { bgcolor: "action.hover" },
                    }}
                    aria-expanded={sectionOpen}
                  >
                    <ListItemText
                      primary={group.title}
                      primaryTypographyProps={{
                        variant: "caption",
                        fontWeight: 700,
                        letterSpacing: 0.4,
                        textTransform: "uppercase",
                        color: "text.secondary",
                      }}
                    />
                    {sectionOpen ? (
                      <ExpandLessIcon fontSize="small" color="action" />
                    ) : (
                      <ExpandMoreIcon fontSize="small" color="action" />
                    )}
                  </ListItemButton>
                ) : null}
                <Collapse in={sectionOpen} timeout="auto" unmountOnExit={false}>
                  <List dense disablePadding component="div">
                    {group.items.map((item) => {
                      const selected = navSelected(pathname, item);
                      const openExternal =
                        item.href === "/guide" || item.href === "/ess";
                      const btn = (
                        <ListItemButton
                          key={item.href}
                          component={Link}
                          href={item.href}
                          target={openExternal ? "_blank" : undefined}
                          rel={openExternal ? "noopener noreferrer" : undefined}
                          selected={!openExternal && selected}
                          onClick={() => setMobileOpen(false)}
                          sx={{
                            justifyContent: collapsed ? "center" : "flex-start",
                            px: collapsed ? 1 : 2,
                            pl: collapsed ? 1 : 2.5,
                          }}
                        >
                          <ListItemIcon
                            sx={{
                              minWidth: collapsed ? 0 : 36,
                              justifyContent: "center",
                              color: selected ? "primary.main" : undefined,
                            }}
                          >
                            {item.icon}
                          </ListItemIcon>
                          {!collapsed ? (
                            <ListItemText primary={item.label} />
                          ) : null}
                        </ListItemButton>
                      );
                      return collapsed ? (
                        <Tooltip
                          key={item.href}
                          title={`${group.title} · ${item.label}`}
                          placement="right"
                        >
                          {btn}
                        </Tooltip>
                      ) : (
                        btn
                      );
                    })}
                  </List>
                </Collapse>
              </List>
            );
          })}
        </Box>
        <Divider />
        <Box sx={{ p: collapsed ? 1 : 2 }}>
          {!collapsed ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {user?.first_name || user?.username || "User"} · {roleLabel}
            </Typography>
          ) : null}
          <Tooltip title="Logout" placement="right">
            <Button
              fullWidth
              startIcon={collapsed ? undefined : <LogoutIcon />}
              onClick={() => {
                localStorage.clear();
                dispatch(logout());
                router.push("/login");
              }}
              sx={{ minWidth: 0, px: collapsed ? 1 : undefined }}
            >
              {collapsed ? <LogoutIcon fontSize="small" /> : "Logout"}
            </Button>
          </Tooltip>
        </Box>
      </Box>
    ),
    [
      collapsed,
      dispatch,
      openSections,
      pathname,
      roleLabel,
      router,
      user,
      visibleGroups,
    ]
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          borderBottom: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          transition: (t) =>
            t.transitions.create(["width", "margin"], {
              easing: t.transitions.easing.sharp,
              duration: t.transitions.duration.enteringScreen,
            }),
        }}
      >
        <Toolbar sx={{ gap: 0.5, minHeight: { xs: 56, sm: 64 } }}>
          <IconButton
            edge="start"
            onClick={() => setMobileOpen(!mobileOpen)}
            sx={{ display: { sm: "none" } }}
            aria-label="Open menu"
          >
            <MenuIcon />
          </IconButton>
          <IconButton
            edge="start"
            onClick={toggleCollapsed}
            sx={{ display: { xs: "none", sm: "inline-flex" } }}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1, minWidth: 0, display: { xs: "none", sm: "block" } }}>
            <Typography variant="subtitle1" fontWeight={600} noWrap>
              {isPlatformUser && !organization
                ? "SI-ERP platform"
                : organization?.brand_tagline ||
                  organization?.brand_name ||
                  organization?.name ||
                  "Accounts · HR · Payroll"}
            </Typography>
          </Box>
          <Box sx={{ flexGrow: 1, display: { xs: "block", sm: "none" } }}>
            <BrandMark size="sm" showName={false} />
          </Box>
          <Tooltip title="User guide (opens in new tab)">
            <IconButton
              component={Link}
              href="/guide"
              target="_blank"
              rel="noopener noreferrer"
              color="default"
              aria-label="User guide"
            >
              <HelpOutlineIcon />
            </IconButton>
          </Tooltip>
          <HeaderNotifications />
          <ThemeToggle />
          <Chip
            size="small"
            label={roleLabel}
            color="primary"
            sx={{ display: { xs: "none", md: "inline-flex" }, maxWidth: 160 }}
          />
          <Chip
            size="small"
            sx={{ display: { xs: "none", sm: "inline-flex" } }}
            label={isPlatformUser && !organization ? "platform" : organization?.code || "tenant"}
            variant="outlined"
          />
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{
          width: { sm: drawerWidth },
          flexShrink: { sm: 0 },
          transition: (t) =>
            t.transitions.create("width", {
              easing: t.transitions.easing.sharp,
              duration: t.transitions.duration.enteringScreen,
            }),
        }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", sm: "none" },
            "& .MuiDrawer-paper": { width: DRAWER_EXPANDED },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          open
          sx={{
            display: { xs: "none", sm: "block" },
            "& .MuiDrawer-paper": {
              width: drawerWidth,
              boxSizing: "border-box",
              overflowX: "hidden",
              transition: (t) =>
                t.transitions.create("width", {
                  easing: t.transitions.easing.sharp,
                  duration: t.transitions.duration.enteringScreen,
                }),
            },
          }}
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          px: { xs: 2, md: 3 },
          py: { xs: 2.5, md: 3 },
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
          maxWidth: 1400,
          transition: (t) =>
            t.transitions.create("width", {
              easing: t.transitions.easing.sharp,
              duration: t.transitions.duration.enteringScreen,
            }),
        }}
      >
        {children}
      </Box>
    </Box>
  );
}
