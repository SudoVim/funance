from rest_framework import serializers

from .models import Fund


class FundSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Fund
        fields = [
            "id",
            "owner",
            "name",
            "currency",
            "available_cash",
        ]
        read_only_fields = ["id", "owner"]
        extra_kwargs = {
            "currency": {"source": "currency_label"},
        }
