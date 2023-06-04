from django.urls import path, include
from rest_framework.routers import DefaultRouter

from funds.api import FundViewSet

router = DefaultRouter()
router.register(r"funds", FundViewSet, basename="fund")

urlpatterns_v1 = [
    path("/", include(router.urls)),
    path("accounts/", include("accounts.api")),
]

urlpatterns = [
    path("v1/", include(urlpatterns_v1)),
]
