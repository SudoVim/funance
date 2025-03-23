import factory

from accounts.factories import AccountFactory
from holdings.models import (
    HoldingAccount,
    HoldingAccountDocument,
    HoldingAccountPosition,
)


class HoldingAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HoldingAccount

    owner = factory.SubFactory(AccountFactory)
    name = factory.Faker("name")
    number = factory.Faker("pystr")
    currency = HoldingAccount.Currency.USD


class HoldingAccountPositionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HoldingAccountPosition

    holding_account = factory.SubFactory(HoldingAccountFactory)
    ticker_symbol = factory.Faker("pystr", max_chars=4)


class HoldingAccountDocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HoldingAccountDocument

    holding_account = factory.SubFactory(HoldingAccountFactory)
    document = factory.Faker("pystr")
    document_type = HoldingAccountDocument.DocumentType.STATEMENT
