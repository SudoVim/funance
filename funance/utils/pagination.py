from rest_framework.pagination import BasePagination
from rest_framework.settings import api_settings


def get_paginator() -> BasePagination:
    paginator = api_settings.DEFAULT_PAGINATION_CLASS
    assert paginator is not None

    return paginator()  # pyright: ignore[reportUnknownVariableType,reportCallIssue]
