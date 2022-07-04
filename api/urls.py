from django.urls import path, include

urlpatterns_v1 = [
    path('accounts/', include('accounts.api')),
]

urlpatterns = [
    path('v1/', include(urlpatterns_v1)),
]
