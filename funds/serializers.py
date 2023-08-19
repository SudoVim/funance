from rest_framework import serializers

from .models import Fund


class FundSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Fund
        fields = [
            "id",
            "name",
            "shares",
        ]
        read_only_fields = ["id"]
