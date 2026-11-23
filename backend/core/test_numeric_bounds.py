from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient, APITestCase

from accounts.models import UserProfile
from accounts.rbac import ensure_default_roles
from core.models import Organization
from core.numeric_bounds import bounds_for
from finance.models import Budget
from ops.models import Item, StockMovement, Warehouse


class NumericBoundTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme",
            code="acme",
            plan_status=Organization.PlanStatus.ACTIVE,
            trial_ends=date.today() + timedelta(days=30),
        )
        User = get_user_model()
        self.user = User.objects.create_user("owner1", password="x-long-password-1")
        UserProfile.objects.create(
            user=self.user, organization=self.org, role=UserProfile.RoleCode.OWNER
        )
        self.org.owner = self.user
        self.org.save()
        ensure_default_roles(self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_budget_year_and_amount_are_bounded(self):
        low = self.client.post(
            "/api/finance/budgets/",
            {"name": "Old", "fiscal_year": 5, "amount": 100},
            format="json",
        )
        self.assertEqual(low.status_code, 400, low.content)
        self.assertIn("2000", str(low.data))

        high = self.client.post(
            "/api/finance/budgets/",
            {"name": "Far", "fiscal_year": 99999, "amount": 100},
            format="json",
        )
        self.assertEqual(high.status_code, 400, high.content)

        negative = self.client.post(
            "/api/finance/budgets/",
            {"name": "Neg", "fiscal_year": 2026, "amount": -10},
            format="json",
        )
        self.assertEqual(negative.status_code, 400, negative.content)
        self.assertIn("negative", str(negative.data).lower())

        ok = self.client.post(
            "/api/finance/budgets/",
            {"name": "FY26", "fiscal_year": 2026, "amount": 1000},
            format="json",
        )
        self.assertEqual(ok.status_code, 201, ok.content)
        self.assertEqual(Budget.objects.get(pk=ok.data["id"]).fiscal_year, 2026)

    def test_stock_movement_qty_may_be_negative(self):
        self.assertEqual(bounds_for("ops", "stockmovement", "qty"), (None, None))
        self.assertEqual(bounds_for("finance", "budget", "amount"), (0, None))
        item = Item.objects.create(organization=self.org, sku="SKU-1", name="Bolt")
        warehouse = Warehouse.objects.create(organization=self.org, code="WH", name="Main")
        movement = StockMovement(
            organization=self.org,
            item=item,
            warehouse=warehouse,
            movement_date=date.today(),
            qty=Decimal("-2"),
        )
        movement.save()
        self.assertEqual(movement.qty, Decimal("-2"))

    def test_direct_negative_budget_amount_is_rejected(self):
        with self.assertRaises(ValidationError):
            Budget.objects.create(
                organization=self.org,
                name="Bad",
                fiscal_year=2026,
                amount=Decimal("-1"),
            )
