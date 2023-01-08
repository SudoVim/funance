from rest_framework import serializers

from .models import Account


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Account
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
        ]
        read_only_fields = ["username", "first_name", "last_name", "email"]
