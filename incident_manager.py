"""
incident_manager.py — Incident reporting and hotspot management.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderServiceError, GeocoderTimedOut

from config import INCIDENTS_FILE, HOTSPOTS_FILE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed hotspot data (15 cities)
# ---------------------------------------------------------------------------
_SEED_HOTSPOTS = [
    {"place": "Delhi",       "lat": 28.61,  "lon":  77.20,  "risk": 0.85, "incident_count": 0},
    {"place": "Mumbai",      "lat": 19.07,  "lon":  72.87,  "risk": 0.75, "incident_count": 0},
    {"place": "New York",    "lat": 40.71,  "lon": -74.00,  "risk": 0.65, "incident_count": 0},
    {"place": "London",      "lat": 51.50,  "lon":  -0.12,  "risk": 0.55, "incident_count": 0},
    {"place": "Paris",       "lat": 48.85,  "lon":   2.35,  "risk": 0.60, "incident_count": 0},
    {"place": "Johannesburg","lat": -26.20, "lon":  28.04,  "risk": 0.90, "incident_count": 0},
    {"place": "Karachi",     "lat": 24.86,  "lon":  67.01,  "risk": 0.80, "incident_count": 0},
    {"place": "Dhaka",       "lat": 23.81,  "lon":  90.41,  "risk": 0.78, "incident_count": 0},
    {"place": "Tokyo",       "lat": 35.67,  "lon": 139.65,  "risk": 0.30, "incident_count": 0},
    {"place": "Sydney",      "lat": -33.86, "lon": 151.20,  "risk": 0.25, "incident_count": 0},
    {"place": "Toronto",     "lat": 43.65,  "lon": -79.38,  "risk": 0.35, "incident_count": 0},
    {"place": "Dubai",       "lat": 25.20,  "lon":  55.27,  "risk": 0.20, "incident_count": 0},
    {"place": "Bangkok",     "lat": 13.75,  "lon": 100.50,  "risk": 0.70, "incident_count": 0},
    {"place": "Mexico City", "lat": 19.43,  "lon": -99.13,  "risk": 0.82, "incident_count": 0},
    {"place": "Rio",         "lat": -22.90, "lon": -43.20,  "risk": 0.88, "incident_count": 0},
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_incidents() -> list[dict]:
    """Load incidents list from disk; return empty list on any error."""
    try:
        with open(INCIDENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("incidents", [])
    except FileNotFoundError:
        return []
    except Exception as exc:
        logger.warning("Could not read incidents file: %s", exc)
        return []


def _save_incidents(incidents: list[dict]) -> None:
    """Persist incidents list to disk."""
    with open(INCIDENTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"incidents": incidents}, f, indent=2)


def _load_hotspots_raw() -> list[dict]:
    """Load hotspots from disk, initialising with seed data if absent."""
    try:
        with open(HOTSPOTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("hotspots", [])
    except FileNotFoundError:
        _save_hotspots(_SEED_HOTSPOTS)
        return list(_SEED_HOTSPOTS)
    except Exception as exc:
        logger.warning("Could not read hotspots file: %s", exc)
        return list(_SEED_HOTSPOTS)


def _save_hotspots(hotspots: list[dict]) -> None:
    """Persist hotspots list to disk."""
    with open(HOTSPOTS_FILE, "w", encoding="utf-8") as f:
        json.dump({"hotspots": hotspots}, f, indent=2)


def _geocode(place: str) -> tuple[Optional[float], Optional[float]]:
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


def _update_hotspot_risk(place: str, hotspots: list[dict]) -> list[dict]:
    """
    Increment incident_count for the matching hotspot (case-insensitive) and
    recalculate risk as min(1.0, base_risk + 0.05 * incident_count).

    If no matching hotspot exists the list is returned unchanged.
    """
    place_lower = place.strip().lower()
    for hs in hotspots:
        if hs.get("place", "").lower() == place_lower:
            hs["incident_count"] = hs.get("incident_count", 0) + 1
            # base_risk is the original seed risk; we approximate it by
            # back-calculating from current values, but the simplest correct
            # approach is to store base_risk separately.  Since the seed data
            # does not include base_risk we derive it on first update:
            if "base_risk" not in hs:
                # On first incident the current risk IS the base risk
                hs["base_risk"] = hs["risk"]
            hs["risk"] = min(1.0, hs["base_risk"] + 0.05 * hs["incident_count"])
            break
    return hotspots


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def report_incident(username: str, place: str, incident_type: str) -> tuple[bool, str]:
    """
    Persist a new incident and update the matching hotspot risk score.

    Returns (True, success_message) or (False, error_message).
    Never raises an exception to the caller.
    """
    try:
        if not place or not place.strip():
            return False, "Location is required"

        lat, lon = _geocode(place)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        incident = {
            "username": username,
            "place": place,
            "lat": lat,
            "lon": lon,
            "type": incident_type,
            "timestamp": timestamp,
        }

        incidents = _load_incidents()
        incidents.append(incident)
        _save_incidents(incidents)

        # Update hotspot risk score
        hotspots = _load_hotspots_raw()
        hotspots = _update_hotspot_risk(place, hotspots)
        _save_hotspots(hotspots)

        return True, "Incident reported successfully."

    except Exception as exc:
        logger.error("report_incident failed: %s", exc)
        return False, f"Failed to report incident: {exc}"


def get_incidents_for_place(place: str) -> list[dict]:
    """
    Return all incidents whose place field matches *place* (case-insensitive).

    Never raises an exception to the caller.
    """
    try:
        place_lower = place.strip().lower()
        incidents = _load_incidents()
        return [i for i in incidents if i.get("place", "").lower() == place_lower]
    except Exception as exc:
        logger.error("get_incidents_for_place failed: %s", exc)
        return []


def load_hotspots() -> list[dict]:
    """
    Return all hotspots from hotspots.json, initialising with seed data if absent.

    Never raises an exception to the caller.
    """
    try:
        return _load_hotspots_raw()
    except Exception as exc:
        logger.error("load_hotspots failed: %s", exc)
        return []
