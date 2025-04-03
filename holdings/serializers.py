from rest_framework import serializers

from .models import HoldingAccount


class HoldingAccountSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = HoldingAccount
        fields = [
            "id",
            "name",
            "currency",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {
            "currency": {"source": "currency_label"},
        }
