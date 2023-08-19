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
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
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


class HoldingAccountPurchaseRequestSerializer(serializers.ModelSerializer):
    holding_account = serializers.UUIDField(required=False)
    ticker = serializers.CharField(
        max_length=Ticker.symbol.field.max_length, required=False
    )

    class Meta:
        model = HoldingAccountPurchase
        fields = [
            "holding_account",
            "ticker",
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
            "created_at",
        ]
        extra_kwargs = {
            "quantity": {"source": "quantity_value"},
            "price": {"source": "price_value"},
        }
