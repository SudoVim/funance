#!/usr/bin/env python3
"""
index database(s) for stock data
"""

import argparse
import sys

from funance_data.tickers.daily import TickerDailyStore
from funance_data.tickers.info import TickerInfoStore

STORES = [
    TickerInfoStore,
    TickerDailyStore,
]


def main(argv: list[str]):
    """main function"""
    parser = argparse.ArgumentParser(
        description="index database(s) for stock data",
    )
    _ = parser.parse_args(argv)

    for store in STORES:
        store.create_index()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
