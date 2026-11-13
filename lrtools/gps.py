"""GPS functions."""

import math
from typing import TYPE_CHECKING

import geopy
from geopy.exc import GeocoderTimedOut

from .lrselectgeneric import LRSelectException

if TYPE_CHECKING:
    from .lrtoolconfig import LRToolConfig

# Earth radius in kilometers
EARTH_RADIUS_KM = 6378.0

type LatLon = tuple[float, float]


def square_around_location(
    lat: float | str, lon: float | str, width: float | str
) -> tuple[LatLon, LatLon]:
    """Return square region around GPS point, width in kilometers."""
    lat = float(lat)
    lon = float(lon)
    width = float(width)
    delta_lat = (width / EARTH_RADIUS_KM) * (180 / math.pi)
    delta_lon = (width / EARTH_RADIUS_KM) * (180 / math.pi) / math.cos(lat * math.pi / 180)
    return (lat - delta_lat, lon - delta_lon), (
        lat + delta_lat,
        lon + delta_lon,
    )


def geocodage(config: LRToolConfig, address: str) -> tuple[LatLon, str] | None:
    """Call to various services to retrieve coordinates and full address from address."""
    geocoder = config.geocoder.lower()
    if geocoder not in {"banfrance", "nominatim"}:
        msg = "None Geocoder"
        raise LRSelectException(msg)
    try:
        details = ""
        if geocoder == "banfrance":
            location = geopy.geocoders.BANFrance().geocode(address, timeout=5)
            details = f" ({location.raw['properties']['postcode']}), {location.raw['properties']['context']}"
        else:
            location = geopy.geocoders.Nominatim(user_agent="lrtools").geocode(address, timeout=5)
        return (
            float(location.latitude),
            float(location.longitude),
        ), str(location.address) + details
    except AttributeError, GeocoderTimedOut:
        return None
