from __future__ import annotations

import logging
from datetime import datetime
from time import struct_time

from rssbot.timezones import MOSCOW_TIMEZONE


def moscow_time_converter(timestamp: float) -> struct_time:
    return datetime.fromtimestamp(timestamp, MOSCOW_TIMEZONE).timetuple()


def configure_moscow_time() -> None:
    logging.Formatter.converter = staticmethod(moscow_time_converter)
