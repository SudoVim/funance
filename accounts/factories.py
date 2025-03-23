import factory

from accounts.models import Account


class AccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Account
