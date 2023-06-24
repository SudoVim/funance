import math
import datetime
import itertools

import pytz
import dateutil.parser
import elasticsearch.helpers
import numpy as np
import pandas as pd
import yfinance as yf

from funance.elastic import client


class TickerOHLC(object):
    """
    object representing the OHLC data for a ticker

    .. attribute:: symbol

        the name of the ticker

    .. automethod:: latest
    """

    def __init__(self, symbol):
        self.symbol = symbol

    def query(self):
        """
        query the daily ohlc data
        """
        today = datetime.datetime.now()
        from_date = today - datetime.timedelta(days=365 * 10)

        latest = self.latest()
        if latest is not None:
            latest_date = latest["_source"]["doc"]["date"]
            now_date = pytz.utc.localize(datetime.datetime.utcnow())
            latest_delta = now_date - latest_date

            # We already have today's data. Just continue.
            if latest_delta < datetime.timedelta(days=1):
                return

            # The last datapoint is from a Friday, and it's currently the
            # weekend. In this case, we also don't have any new datapoints to
            # gather.
            if latest_date.weekday() == 4 and now_date.weekday() in [5, 6]:
                return

            from_date = latest_date + datetime.timedelta(days=1)

        try:
            df = yf.Ticker(self.symbol).history(start=from_date, end=today)
            df["Adj Close"] = df["Close"]

        except (KeyError, pandas_datareader._utils.RemoteDataError):
            return

        def bulk_upload(dates, data):
            for date, row in zip(dates, data):
                entry = {c: e for c, e in zip(df.columns, row)}
                entry["symbol"] = self.symbol
                entry["date"] = date
                yield {
                    "_op_type": "update",
                    "_index": "funance-ohlc",
                    "_id": "%s-%s" % (self.symbol, entry["date"]),
                    "doc": {"doc": entry},
                    "doc_as_upsert": True,
                }

        for _ in elasticsearch.helpers.streaming_bulk(
            client(),
            bulk_upload(df.index, df.values),
        ):
            pass

    def latest(self):
        """
        the latest ohlc datapoint
        """
        results = client().search(
            index="funance-ohlc",
            body={
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "doc.symbol": {
                                        "query": self.symbol,
                                        "operator": "and",
                                    },
                                },
                            },
                        ],
                    },
                },
                "sort": [
                    {
                        "doc.date": {
                            "order": "desc",
                        },
                    },
                ],
            },
            size=1,
            request_timeout=300,
        )
        hits = results["hits"]["hits"]

        if not hits:
            return None

        return self.encode_entry(hits[0])

    def daily_iter(self, start_date=None):
        """
        iterate over all daily entries
        """
        while True:
            body = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "match": {
                                    "doc.symbol": {
                                        "query": self.symbol,
                                        "operator": "and",
                                    },
                                },
                            },
                        ],
                    },
                },
                "sort": [
                    {
                        "doc.date": {
                            "order": "asc",
                        },
                    },
                ],
            }

            if start_date is not None:
                body["query"]["bool"]["filter"] = {
                    "range": {
                        "doc.date": {
                            "gt": start_date,
                        },
                    },
                }

            results = client().search(
                index="funance-ohlc",
                body=body,
                size=10000,
                request_timeout=300,
            )
            hits = results["hits"]["hits"]
            for hit in hits:
                yield self.encode_entry(hit)

            if len(hits) < 10000:
                break

            if hits:
                start_date = hits[-1]["_source"]["doc"]["date"]

    @staticmethod
    def encode_entry(entry):
        """
        encode the given entry for the user
        """
        entry["_source"]["doc"]["date"] = dateutil.parser.parse(
            entry["_source"]["doc"]["date"]
        )

        return entry

    def daily(self, start_date=None):
        """
        get a daily list of ohlc datapoints
        """
        return list(self.daily_iter(start_date))

    def daily_pandas(self, features, processed_features):
        """
        get a pandas dataframe containing all datapoints
        """
        arr = np.array(
            [
                tuple(
                    itertools.chain(
                        (e["_source"]["doc"]["date"],),
                        (e["_source"]["doc"][f] for f in features),
                        (
                            e["_source"]["doc"]["processed"].get(f, None)
                            for f in processed_features
                        ),
                    ),
                )
                for e in self.daily_iter()
                if "processed" in e["_source"]["doc"]
            ],
            dtype=list(
                itertools.chain(
                    (("date", "M8[D]"),),
                    ((f, "<f8") for f in features),
                    ((f, "<f8") for f in processed_features),
                ),
            ),
        )

        return pd.DataFrame(data=arr[features + processed_features], index=arr["date"])

    def process_ticker(self, start_date=None):
        """
        process the ticker for datascience
        """
        arr = np.array(
            [
                (
                    e["_source"]["doc"]["date"],
                    e["_id"],
                    e["_source"]["doc"]["Close"],
                    e["_source"]["doc"]["Adj Close"],
                    e["_source"]["doc"]["Volume"],
                )
                for e in self.daily_iter(start_date)
            ],
            dtype=[
                ("date", "M8[D]"),
                ("id", "U32"),
                ("Close", "<f8"),
                ("Adj Close", "<f8"),
                ("Volume", "<f8"),
            ],
        )

        raw_columns = ["id", "Close", "Adj Close", "Volume"]
        df = pd.DataFrame(
            data=arr[raw_columns],
            index=arr["date"],
        )

        resamples = {}
        for resample_period in [
            "5D",
            "10D",
            "30D",
            "90D",
            "180D",
            "360D",
            "540D",
            "720D",
        ]:
            resample = {}
            resample["Adj Close"] = df["Adj Close"].resample(resample_period).ohlc()
            resample["Volume"] = df["Volume"].resample(resample_period).sum()
            resamples[resample_period] = resample

        for rolling_window in [5, 10, 20, 30, 50, 90, 180, 360, 540, 720]:
            df["adjusted_close_avg_%sd" % rolling_window] = (
                df["Adj Close"].rolling(rolling_window).mean()
            )
            df["adjusted_close_median_%sd" % rolling_window] = (
                df["Adj Close"].rolling(rolling_window).median()
            )
            df["volume_avg_%sd" % rolling_window] = (
                df["Volume"].rolling(rolling_window).mean()
            )
            df["volume_median_%sd" % rolling_window] = (
                df["Volume"].rolling(rolling_window).median()
            )

        for shift_period in [-5, -10, -20, -30, -50, -90, -180, -360, -540, -720]:
            df["adjusted_close_shift_%sd" % (-shift_period)] = df["Adj Close"].shift(
                shift_period
            )
            df["volume_shift_%sd" % (-shift_period)] = df["Volume"].shift(shift_period)

        def bulk_update(columns, values):
            for entry in values:
                processed_data = {}

                for column, value in zip(
                    columns[len(raw_columns) :], entry[len(raw_columns) :]
                ):
                    if math.isnan(value):
                        continue

                    processed_data[column] = value

                processed_data["Adj Close"] = entry[2]

                yield {
                    "_op_type": "update",
                    "_index": "funance-ohlc",
                    "_id": entry[0],
                    "doc": {
                        "doc": {"processed": processed_data},
                    },
                }

        for _ in elasticsearch.helpers.streaming_bulk(
            client(),
            bulk_update(df.columns, df.values),
            raise_on_error=False,
        ):
            pass

    @classmethod
    def latest_batch(cls, start_date=None):
        """
        query an array of the latest day of ohlc data
        """
        if start_date is None:
            start_date = datetime.date.today()

        hits = []
        for days in range(5):
            results = client().search(
                index="funance-ohlc",
                body={
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "match": {
                                        "doc.date": {
                                            "query": start_date,
                                            "operator": "and",
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
                size=10000,
                request_timeout=300,
            )
            hits = results["hits"]["hits"]
            if hits:
                break

            start_date -= datetime.timedelta(days=1)

        if not hits:
            return None

        return (start_date, [cls.encode_entry(h) for h in hits])

    @classmethod
    def latest_batch_pandas(cls, features, processed_features, start_date=None):
        """
        get a pandas dataframe containing all datapoints
        """
        latest_batch = cls.latest_batch(start_date)
        if not latest_batch:
            return None

        arr = np.array(
            [
                tuple(
                    itertools.chain(
                        (e["_source"]["doc"]["date"], e["_source"]["doc"]["symbol"]),
                        (e["_source"]["doc"][f] for f in features),
                        (
                            e["_source"]["doc"]["processed"].get(f, None)
                            for f in processed_features
                        ),
                    ),
                )
                for e in latest_batch[1]
                if "processed" in e["_source"]["doc"]
            ],
            dtype=list(
                itertools.chain(
                    (("date", "M8[D]"), ("symbol", np.unicode_, 8)),
                    ((f, "<f8") for f in features),
                    ((f, "<f8") for f in processed_features),
                ),
            ),
        )

        return pd.DataFrame(
            data=arr[["symbol"] + features + processed_features], index=arr["date"]
        )
