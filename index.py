#!/usr/bin/env python3
"""
index database(s) for stock data
"""

import sys
import argparse

from funance.elastic import client
from funance_data.tickers.info import TickerInfoStore
from funance_data.tickers.daily import TickerDailyStore

from django.conf import settings


STORES = [
    TickerInfoStore,
    TickerDailyStore,
]


def main(argv):
    """main function"""
    parser = argparse.ArgumentParser(
        description="index database(s) for stock data",
    )
    parser.parse_args(argv)

    for store in STORES:
        import pdb

        pdb.set_trace()
        store.create_index()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
