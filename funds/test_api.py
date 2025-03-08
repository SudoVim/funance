import collections
import datetime

from django.test import TestCase
from knox.models import AuthToken
from rest_framework.exceptions import ErrorDetail
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account
from tickers.models import Ticker

from .api import FundAllocationViewSet, FundViewSet
from .models import Fund, FundAllocation


class BaseFundTestCase(TestCase):
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


class FundsTestCase(BaseFundTestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.maxDiff = None

    def test_create_fund_unauthed(self):
        request = self.factory.post("/api/v1/funds")
        response = FundViewSet.as_view({"post": "create"})(request)
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

    def test_create_fund_empty(self):
        request = self.factory.post("/api/v1/funds")
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"post": "create"})(request)
        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {
                "name": [
                    ErrorDetail(
                        "This field is required.",
                        code="required",
                    ),
                ],
            },
            response.data,
        )

    def test_create_fund(self):
        request = self.factory.post(
            "/api/v1/funds",
            {
                "name": "Fund Name",
            },
        )
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"post": "create"})(request)
        self.assertEqual(201, response.status_code)
        self.assertEqual(
            {
                "id": response.data["id"],
                "name": "Fund Name",
                "shares": 1000,
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            response.data,
        )

    def test_create_fund_optional(self):
        request = self.factory.post(
            "/api/v1/funds",
            {
                "name": "Fund Name",
                "shares": 2000,
            },
        )
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"post": "create"})(request)
        self.assertEqual(201, response.status_code)
        self.assertEqual(
            {
                "id": response.data["id"],
                "name": "Fund Name",
                "shares": 2000,
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            response.data,
        )

    def test_funds_empty(self):
        request = self.factory.get("/api/v1/funds")
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"get": "list"})(request)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            collections.OrderedDict(
                [
                    ("count", 0),
                    ("next", None),
                    ("previous", None),
                    ("results", []),
                ]
            ),
            response.data,
        )

    def test_funds(self):
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        request = self.factory.get("/api/v1/funds")
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"get": "list"})(request)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            collections.OrderedDict(
                [
                    ("count", 1),
                    ("next", None),
                    ("previous", None),
                    (
                        "results",
                        [
                            collections.OrderedDict(
                                [
                                    ("id", str(fund.id)),
                                    ("name", "Fund Name"),
                                    ("shares", 1000),
                                    (
                                        "created_at",
                                        response.data["results"][0]["created_at"],
                                    ),
                                    (
                                        "updated_at",
                                        response.data["results"][0]["updated_at"],
                                    ),
                                ]
                            ),
                        ],
                    ),
                ]
            ),
            response.data,
        )

    def test_retrieve_fund_404(self):
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        request = self.factory.get("/api/v1/funds/invalid")
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"get": "retrieve"})(request, pk="invalid")
        self.assertEqual(404, response.status_code)
        self.assertEqual(
            {
                "detail": ErrorDetail("Not found.", code="not_found"),
            },
            response.data,
        )

    def test_retrieve_fund(self):
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        request = self.factory.get(f"/api/v1/funds/{fund.pk}")
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"get": "retrieve"})(request, pk=fund.pk)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "id": response.data["id"],
                "name": "Fund Name",
                "shares": 1000,
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            response.data,
        )

    def test_partial_update_empty(self):
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        request = self.factory.patch(f"/api/v1/funds/{fund.pk}")
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"patch": "partial_update"})(request, pk=fund.pk)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "id": response.data["id"],
                "name": "Fund Name",
                "shares": 1000,
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            response.data,
        )

    def test_partial_update_single(self):
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        request = self.factory.patch(
            f"/api/v1/funds/{fund.pk}",
            {
                "shares": 2000,
            },
        )
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"patch": "partial_update"})(request, pk=fund.pk)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "id": response.data["id"],
                "name": "Fund Name",
                "shares": 2000,
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            response.data,
        )

    def test_create_allocation_empty(self):
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        request = self.factory.post(
            f"/api/v1/funds/{fund.pk}",
        )
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"post": "create_allocation"})(
            request, pk=fund.pk
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {
                "ticker": [
                    ErrorDetail("This field is required.", code="required"),
                ],
            },
            response.data,
        )

    def test_create_allocation(self):
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        request = self.factory.post(
            f"/api/v1/funds/{fund.pk}",
            {
                "ticker": "MSFT",
            },
        )
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"post": "create_allocation"})(
            request, pk=fund.pk
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "id": response.data["id"],
                "fund": fund.pk,
                "ticker": collections.OrderedDict(
                    [
                        ("symbol", "MSFT"),
                    ]
                ),
                "shares": 0,
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            response.data,
        )

    def test_create_allocation_ticker_exist(self):
        ticker = Ticker.objects.create(symbol="MSFT")
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        request = self.factory.post(
            f"/api/v1/funds/{fund.pk}",
            {
                "ticker": "MSFT",
            },
        )
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"post": "create_allocation"})(
            request, pk=fund.pk
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "id": response.data["id"],
                "fund": fund.pk,
                "ticker": collections.OrderedDict(
                    [
                        ("symbol", "MSFT"),
                    ]
                ),
                "shares": 0,
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            response.data,
        )

    def test_list_allocations_empty(self):
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        request = self.factory.get(f"/api/v1/funds/{fund.pk}")
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"get": "allocations"})(request, pk=fund.pk)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            collections.OrderedDict(
                [
                    ("count", 0),
                    ("next", None),
                    ("previous", None),
                    ("results", []),
                ]
            ),
            response.data,
        )

    def test_list_allocations(self):
        fund = Fund.objects.create(owner=self.account, name="Fund Name")
        ticker = Ticker.objects.create(symbol="MSFT")
        allocation = FundAllocation.objects.create(fund=fund, ticker=ticker, shares=5)
        request = self.factory.get(f"/api/v1/funds/{fund.pk}")
        force_authenticate(request, self.account, self.token)
        response = FundViewSet.as_view({"get": "allocations"})(request, pk=fund.pk)
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            collections.OrderedDict(
                [
                    ("count", 1),
                    ("next", None),
                    ("previous", None),
                    (
                        "results",
                        [
                            collections.OrderedDict(
                                [
                                    ("id", str(allocation.id)),
                                    ("fund", fund.id),
                                    (
                                        "ticker",
                                        collections.OrderedDict([("symbol", "MSFT")]),
                                    ),
                                    ("shares", 5),
                                    (
                                        "created_at",
                                        response.data["results"][0]["created_at"],
                                    ),
                                    (
                                        "updated_at",
                                        response.data["results"][0]["updated_at"],
                                    ),
                                ]
                            ),
                        ],
                    ),
                ]
            ),
            response.data,
        )


class FundAllocationsTestCase(BaseFundTestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.maxDiff = None
        self.fund = Fund.objects.create(owner=self.account, name="Fund Name")
        self.ticker = Ticker.objects.create(symbol="MSFT")
        self.allocation = FundAllocation.objects.create(
            fund=self.fund, ticker=self.ticker, shares=5
        )

    def test_retrieve_unauthed(self):
        request = self.factory.get(f"/api/v1/fund_allocations/{self.allocation.pk}")
        response = FundAllocationViewSet.as_view({"get": "retrieve"})(
            request, pk=self.allocation.pk
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

    def test_retrieve(self):
        request = self.factory.get(f"/api/v1/fund_allocations/{self.allocation.pk}")
        force_authenticate(request, self.account, self.token)
        response = FundAllocationViewSet.as_view({"get": "retrieve"})(
            request, pk=self.allocation.pk
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {
                "id": str(self.allocation.id),
                "fund": self.fund.pk,
                "ticker": collections.OrderedDict(
                    [
                        ("symbol", "MSFT"),
                    ]
                ),
                "shares": 5,
                "created_at": response.data["created_at"],
                "updated_at": response.data["updated_at"],
            },
            response.data,
        )
