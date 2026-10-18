"""
library for interfacing with elasticsearch
"""

import threading

import elasticsearch
from django.conf import settings

app_local = threading.local()


def client():
    """
    connect and return the elasticsearch client object
    """
    if not hasattr(app_local, "global_elastic_client"):
        # TODO: This information needs to be configurable. I'm only using the
        # default host/auth here.
        app_local.global_elastic_client = elasticsearch.Elasticsearch(
            [settings.ELASTICSEARCH_URL],
            http_auth=(
                settings.ELASTICSEARCH_USERNAME,
                settings.ELASTICSEARCH_PASSWORD,
            ),
        )

    return app_local.global_elastic_client
