"""
library for interfacing with elasticsearch
"""

import threading

import elasticsearch

app_local = threading.local()

def client():
    """
        connect and return the elasticsearch client object
    """
    if not hasattr(app_local, 'global_elastic_client'):
        # TODO: This information needs to be configurable. I'm only using the
        # default host/auth here.
        app_local.global_elastic_client = elasticsearch.Elasticsearch(
            ['http://elastic:9200'],
            http_auth=('elastic', 'changeme'),
        )

    return app_local.global_elastic_client
