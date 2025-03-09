from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import BaseRouter
from rest_framework.serializers import BaseSerializer
from typing_extensions import override

from .models import HoldingAccount
from .serializers import (
    HoldingAccountSerializer,
)


class HoldingAccountViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    View and edit holding accounts
    """

    serializer_class = HoldingAccountSerializer
    permission_classes = [IsAuthenticated]

    @override
    def get_queryset(self) -> QuerySet[HoldingAccount]:
        return (
            HoldingAccount.objects.filter(
                owner=self.request.user,
            )
            .order_by("name")
            .all()
        )

    @override
    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.save(owner=self.request.user)


def register_routes(router: BaseRouter):
    router.register(
        "holding_accounts", HoldingAccountViewSet, basename="holdingaccount"
    )
