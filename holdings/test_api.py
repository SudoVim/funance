import datetime

from django.test import TestCase
from knox.models import AuthToken
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account

from .api import HoldingAccountViewSet
from .models import HoldingAccount


class BaseHoldingAccountTestCase(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            username="GGreggs",
            first_name="Greg",
            last_name="Greggs",
            email="ggreggs@example.com",
        )
        self.token, _ = AuthToken.objects.create(
            self.account, datetime.timedelta(hours=10)
        )


class HoldingAccountsTestCase(BaseHoldingAccountTestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.maxDiff = None

    def test_account_holdings_unauthed(self):
        request = self.factory.get("/api/v1/holding_accounts")
        response = HoldingAccountViewSet.as_view({"get": "list"})(request)
        self.assertEqual(401, response.status_code)
        self.assertEqual(
            {
                "detail": ErrorDetail(
                    "Authentication credentials were not provided.",
                    code="not_authenticated",
                ),
            },
            response.data,
        )

    def test_account_holdings_empty(self):
        request = self.factory.get("/api/v1/holding_accounts")
        force_authenticate(request, self.account, self.token)
        response = HoldingAccountViewSet.as_view({"get": "list"})(request)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            },
            response.data,
        )

    def test_account_holdings_with_holding(self):
        ha = HoldingAccount.objects.create(
            owner=self.account,
            name="My Holding Account",
            currency=HoldingAccount.Currency.USD,
        )
        request = self.factory.get("/api/v1/holding_accounts")
        force_authenticate(request, self.account, self.token)
        response = HoldingAccountViewSet.as_view({"get": "list"})(request)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": str(ha.id),
                        "name": "My Holding Account",
                        "currency": "USD",
                        "created_at": response.data["results"][0]["created_at"],
                        "updated_at": response.data["results"][0]["updated_at"],
                    },
                ],
            },
            response.data,
        )

    def test_account_holdings_other_user(self):
        ha = HoldingAccount.objects.create(
            owner=self.account,
            name="My Holding Account",
            currency=HoldingAccount.Currency.USD,
        )
        other_account = Account.objects.create(
            username="SSteves",
            first_name="Steve",
            last_name="Steves",
            email="ssteves@example.com",
        )
        other_token, _ = AuthToken.objects.create(
            other_account, datetime.timedelta(hours=10)
        )
        request = self.factory.get("/api/v1/holding_accounts")
        force_authenticate(request, other_account, other_token)
        response = HoldingAccountViewSet.as_view({"get": "list"})(request)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "count": 0,
                "next": None,
                "previous": None,
                "results": [],
            },
            response.data,
        )

    def test_create(self):
        request = self.factory.post(
            "/api/v1/holding_accounts",
            {
                "name": "My New Account",
            },
        )
        force_authenticate(request, self.account, self.token)
        response = HoldingAccountViewSet.as_view({"post": "create"})(request)
        self.assertEqual(201, response.status_code)
        self.assertEqual(
            {
                "id": response.data["id"],
                "name": "My New Account",
                "currency": "USD",
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            dict(response.data),
        )


class HoldingAccountTestCase(BaseHoldingAccountTestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.maxDiff = None

        self.ha = HoldingAccount.objects.create(
            owner=self.account,
            name="My Holding Account",
            currency=HoldingAccount.Currency.USD,
        )

    def test_get_unauthed(self):
        request = self.factory.get(f"/api/v1/holding_accounts/{self.ha.pk}")
        response = HoldingAccountViewSet.as_view({"get": "retrieve"})(
            request, self.ha.pk
        )
        self.assertEqual(401, response.status_code)
        self.assertEqual(
            {
                "detail": ErrorDetail(
                    "Authentication credentials were not provided.",
                    code="not_authenticated",
                ),
            },
            response.data,
        )

    def test_get(self):
        request = self.factory.get(f"/api/v1/holding_accounts/{self.ha.pk}")
        force_authenticate(request, self.account, self.token)
        response = HoldingAccountViewSet.as_view({"get": "retrieve"})(
            request, pk=self.ha.pk
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "id": str(self.ha.id),
                "name": "My Holding Account",
                "currency": "USD",
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            response.data,
        )

    def test_update(self):
        request = self.factory.patch(
            f"/api/v1/holding_accounts/{self.ha.pk}",
            {
                "name": "New name",
            },
        )
        force_authenticate(request, self.account, self.token)
        response = HoldingAccountViewSet.as_view({"patch": "partial_update"})(
            request, pk=self.ha.pk
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "id": str(self.ha.id),
                "name": "New name",
                "currency": "USD",
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            dict(response.data),
        )
