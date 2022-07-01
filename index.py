#!/usr/bin/env python3
"""
index database(s) for stock data
"""

import sys
import argparse

from funance.elastic import client

def main(argv):
    """ main function """
    parser = argparse.ArgumentParser(
        description="index database(s) for stock data",
    )
    args = parser.parse_args(argv)

    c = client()
    for index in ['funance-ohlc']:
        if not c.indices.exists(index):
            c.indices.create(index=index)

    c.indices.put_mapping(
        index='funance-ohlc',
        body={
            'properties': {
                'doc.date': {
                    'type': 'date',
                },
            },
        },
    )

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
