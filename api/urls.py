from django.urls import path, include
from rest_framework.routers import DefaultRouter

import funds.api
import holdings.api

router = DefaultRouter()
funds.api.register_routes(router)
holdings.api.register_routes(router)

urlpatterns_v1 = [
    path("", include(router.urls)),
    path("accounts/", include("accounts.api")),
]

urlpatterns = [
    path("v1/", include(urlpatterns_v1)),
]
