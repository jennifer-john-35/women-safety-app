"""
route_analyzer.py — Safe route analysis between two locations.
"""
import logging
from typing import Union

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut

from incident_manager import load_hotspots
from risk_engine import classify_risk

logger = logging.getLogger(__name__)

_SAFE_ZONES = ["Police Station", "Hospital", "Metro Station", "Shopping Mall"]
_PROXIMITY_DEGREES = 5.0


def _geocode(place: str):
    """Return (lat, lon) for *place* via Nominatim, or (None, None) on failure."""
    try:
        geolocator = Nominatim(user_agent="ai_women_safety_system")
        location = geolocator.geocode(place, timeout=10)
        if location:
            return location.latitude, location.longitude
    except (GeocoderServiceError, GeocoderTimedOut) as exc:
        logger.warning("Geocoding failed for '%s': %s", place, exc)
    except Exception as exc:
        logger.warning("Unexpected geocoding error for '%s': %s", place, exc)
    return None, None


def analyze_route(source: str, destination: str) -> Union[dict, tuple]:
    """Evaluate route safety between source and destination.

    Returns a dict with keys:
        risk_score     — float in [0.0, 1.0]
        classification — 'HIGH', 'MODERATE', or 'LOW'
        safe_zones     — list of nearby safe zone category names

    Returns (False, "Source and destination are required") when either
    input is blank.  Never raises an exception to the caller.
    """
    try:
        if not source or not source.strip() or not destination or not destination.strip():
            return False, "Source and destination are required"

        src_lat, src_lon = _geocode(source.strip())
        dst_lat, dst_lon = _geocode(destination.strip())

        hotspots = load_hotspots()

        risk_scores = []
        for hs in hotspots:
            hs_lat = hs.get("lat")
            hs_lon = hs.get("lon")
            hs_risk = hs.get("risk", 0.0)

            if hs_lat is None or hs_lon is None:
                continue

            # Check proximity to source endpoint
            if src_lat is not None and src_lon is not None:
                if (abs(hs_lat - src_lat) <= _PROXIMITY_DEGREES and
                        abs(hs_lon - src_lon) <= _PROXIMITY_DEGREES):
                    risk_scores.append(hs_risk)
                    continue

            # Check proximity to destination endpoint
            if dst_lat is not None and dst_lon is not None:
                if (abs(hs_lat - dst_lat) <= _PROXIMITY_DEGREES and
                        abs(hs_lon - dst_lon) <= _PROXIMITY_DEGREES):
                    risk_scores.append(hs_risk)

        if risk_scores:
            raw_score = sum(risk_scores) / len(risk_scores)
        else:
            raw_score = 0.0

        risk_score = max(0.0, min(1.0, raw_score))
        classification = classify_risk(risk_score)

        return {
            "risk_score": risk_score,
            "classification": classification,
            "safe_zones": list(_SAFE_ZONES),
        }

    except Exception as exc:
        logger.error("analyze_route failed: %s", exc)
        return {
            "risk_score": 0.0,
            "classification": classify_risk(0.0),
            "safe_zones": list(_SAFE_ZONES),
        }
