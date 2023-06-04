from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import Account

from .api import FundViewSet
from .models import Fund


class BaseFundTestCase(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            username="GGreggs",
            first_name="Greg",
            last_name="Greggs",
            email="ggreggs@example.com",
        )


class FundsTestCase(BaseFundTestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.maxDiff = None
