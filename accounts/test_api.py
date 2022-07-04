import datetime
import unittest.mock

from knox.models import AuthToken
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.exceptions import ErrorDetail

from accounts.models import Account

from .api import LoginAPI, LogoutAPI, LogoutAllAPI

def mock_login():
    def fcn(request, user):
        request.user = user
    return unittest.mock.patch('accounts.api.login', autospec=True, side_effect=fcn)

class BaseAccountTestCase(TestCase):

    def setUp(self):
        self.account = Account.objects.create(
            username='GGreggs',
            first_name='Greg',
            last_name='Greggs',
            email='ggreggs@example.com',
        )

        self.account.set_password('password')
        self.account.save()

class LoginTestCase(BaseAccountTestCase):

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.maxDiff = None

    def test_login_empty(self):
        request = self.factory.post("/api/v1/accounts/login")
        response = LoginAPI.as_view()(request)
        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {
                'password': [ErrorDetail('This field is required.', code='required')],
                'username': [ErrorDetail('This field is required.', code='required')],
            },
            response.data,
        )

    def test_login_failure(self):
        request = self.factory.post("/api/v1/accounts/login", {
            'username': 'GGreggs',
            'password': 'invalid',
        })
        response = LoginAPI.as_view()(request)
        self.assertEqual(400, response.status_code)
        self.assertEqual(
            {
                'non_field_errors': [ErrorDetail('Unable to log in with provided credentials.', code='authorization')],
            },
            response.data,
        )

    @mock_login()
    def test_login_success(self, fake_login):
        request = self.factory.post("/api/v1/accounts/login", {
            'username': 'GGreggs',
            'password': 'password',
        })
        response = LoginAPI.as_view()(request)
        self.assertEqual(200, response.status_code)

        fake_login.assert_called_once()

class LogoutTestCase(BaseAccountTestCase):

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.maxDiff = None

    def test_logout_not_logged_in(self):
        request = self.factory.post("/api/v1/accounts/logout")
        response = LogoutAPI.as_view()(request)
        self.assertEqual(401, response.status_code)
        self.assertEqual(
            {
                'detail': ErrorDetail(
                    'Authentication credentials were not provided.',
                    code='not_authenticated',
                ),
            },
            response.data,
        )

    def test_logout_success(self):
        instance, _ = AuthToken.objects.create(self.account, datetime.timedelta(hours=10))
        request = self.factory.post("/api/v1/accounts/logout", _auth=instance)
        force_authenticate(request, self.account, instance)

        response = LogoutAPI.as_view()(request)
        self.assertEqual(204, response.status_code)
        self.assertEqual(0, AuthToken.objects.count())

class LogoutAllTestCase(BaseAccountTestCase):

    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.maxDiff = None

    def test_logoutall_not_logged_in(self):
        request = self.factory.post("/api/v1/accounts/logoutall")
        response = LogoutAllAPI.as_view()(request)
        self.assertEqual(401, response.status_code)
        self.assertEqual(
            {
                'detail': ErrorDetail(
                    'Authentication credentials were not provided.',
                    code='not_authenticated',
                ),
            },
            response.data,
        )

    def test_logoutall_success(self):
        instance, _ = AuthToken.objects.create(self.account, datetime.timedelta(hours=10))

        # Make a couple more
        AuthToken.objects.create(self.account, datetime.timedelta(hours=10))
        AuthToken.objects.create(self.account, datetime.timedelta(hours=10))

        request = self.factory.post("/api/v1/accounts/logoutall", _auth=instance)
        force_authenticate(request, self.account, instance)

        response = LogoutAllAPI.as_view()(request)
        self.assertEqual(204, response.status_code)
        self.assertEqual(0, AuthToken.objects.count())
