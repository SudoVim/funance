from rest_framework import serializers
from rest_framework.fields import empty

from tickers.models import Ticker
from tickers.serializers import TickerSerializer

from .models import HoldingAccount, HoldingAccountPurchase


class HoldingAccountSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = HoldingAccount
        fields = [
            "id",
            "name",
            "currency",
            "available_cash",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "currency": {"source": "currency_label"},
            "available_cash": {"source": "available_cash_value"},
        }


class CreateHoldingAccountPurchaseSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(max_length=Ticker.symbol.field.max_length)

    class Meta:
        model = HoldingAccountPurchase
        fields = [
            "ticker",
            "quantity",
            "price",
            "purchased_at",
        ]


class HoldingAccountPurchaseSerializer(serializers.HyperlinkedModelSerializer):
    ticker = TickerSerializer()

    class Meta:
        model = HoldingAccountPurchase
        fields = [
            "id",
            "holding_account",
            "ticker",
            "quantity",
            "price",
            "purchased_at",
        ]
        extra_kwargs = {
            "quantity": {"source": "quantity_value"},
            "price": {"source": "price_value"},
        }
