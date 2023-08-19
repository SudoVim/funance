from rest_framework import serializers

from tickers.models import Ticker
from tickers.serializers import TickerSerializer

from .models import Fund, FundAllocation


class FundSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Fund
        fields = [
            "id",
            "name",
            "shares",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CreateFundAllocationSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(max_length=Ticker.symbol.field.max_length)

    class Meta:
        model = FundAllocation
        fields = [
            "ticker",
            "shares",
        ]


class FundAllocationSerializer(serializers.ModelSerializer):
    ticker = TickerSerializer()

    class Meta:
        model = FundAllocation
        fields = [
            "id",
            "fund",
            "ticker",
            "shares",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "fund",
            "ticker",
            "created_at",
            "updated_at",
        ]
