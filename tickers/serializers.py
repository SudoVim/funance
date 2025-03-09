from rest_framework import serializers

from .models import Ticker


class TickerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Ticker
        fields = [
            "symbol",
        ]
        read_only_fields = ["symbol"]
