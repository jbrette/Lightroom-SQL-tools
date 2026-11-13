"""Lightroom dates : timestamps are seconds from 2001-01-01 UTC, capture times are ISO strings."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytz
import tzlocal
from dateutil import parser

if TYPE_CHECKING:
    from .lrtoolconfig import LRToolConfig

# date reference of lightroom (at least for timestamp of photos modified)
LIGHTROOM_EPOCH = datetime(2001, 1, 1, 0, 0, 0, tzinfo=UTC)
# unix timestamp for LR epoch (2001,1,1,0,0,0)
TIMESTAMP_LR_EPOCH = 978307200


def date_to_lrstamp(config: LRToolConfig, mydate: object, *, localtz: bool = True) -> float | None:
    """Convert localized time string or datetime date to a lightroom timestamp.

    The timestamp is seconds (float) from 1/1/2001; None if mydate is neither a str nor a datetime.
    """
    if isinstance(mydate, str):
        dtdate = parser.parse(mydate, dayfirst=config.dayfirst)
        # set locale timezone
        if localtz:
            dtdate = dtdate.astimezone(tzlocal.get_localzone())
        else:
            dtdate = dtdate.astimezone(pytz.utc)
    elif isinstance(mydate, datetime):
        dtdate = mydate
    else:
        return None
    ts = (dtdate - LIGHTROOM_EPOCH).total_seconds()
    return max(ts, 0)


def lr_strptime(lrdate: str) -> datetime:
    """Convert LR date string to datetime.

    Strings without UTC offset give naive datetimes, as Lightroom stores them.
    """
    if "." in lrdate:
        if "+" in lrdate:
            # format 2019-08-13T19:47:33.022+02:00
            return datetime.strptime(lrdate, "%Y-%m-%dT%H:%M:%S.%f%z")
        # format 2019-08-13T19:47:33.269
        return datetime.strptime(lrdate, "%Y-%m-%dT%H:%M:%S.%f")  # noqa: DTZ007 naive as stored
    if "+" in lrdate or "Z" in lrdate:
        # format 2019-08-13T19:47:33+02:00
        try:
            return datetime.strptime(lrdate, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            pass
        return datetime.strptime(lrdate, "%Y-%m-%dT%H:%M%z")
    # format 2019-08-13T19:47:33
    try:
        return datetime.strptime(lrdate, "%Y-%m-%dT%H:%M:%S")  # noqa: DTZ007 naive as stored
    except ValueError:
        pass
    return datetime.strptime(lrdate, "%Y-%m-%dT%H:%M")  # noqa: DTZ007 naive as stored
