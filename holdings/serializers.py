from rest_framework import serializers
from rest_framework.fields import empty

from .models import HoldingAccount


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
