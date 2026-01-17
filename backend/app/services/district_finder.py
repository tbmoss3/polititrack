"""District finder service using Census Geocoding API."""

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/address"


@dataclass
class DistrictResult:
    """Result from district lookup."""

    state: str
    state_name: str
    district: int | None
    formatted_address: str | None = None
    lat: float | None = None
    lng: float | None = None


async def find_district_by_address(
    street: str,
    city: str,
    state: str,
    zip_code: str | None = None,
) -> DistrictResult | None:
    """
    Find congressional district from a street address.

    Uses the US Census Bureau Geocoding API which is free and doesn't require API keys.

    Args:
        street: Street address (e.g., "1600 Pennsylvania Ave NW")
        city: City name (e.g., "Washington")
        state: State abbreviation (e.g., "DC")
        zip_code: Optional ZIP code

    Returns:
        DistrictResult with state and district info, or None if not found
    """
    params = {
        "street": street,
        "city": city,
        "state": state,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "layers": "54",  # Congressional Districts layer
        "format": "json",
    }

    if zip_code:
        params["zip"] = zip_code

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(CENSUS_GEOCODER_URL, params=params)
            response.raise_for_status()
            data = response.json()

        result = data.get("result", {})
        address_matches = result.get("addressMatches", [])

        if not address_matches:
            logger.warning(f"No address matches found for: {street}, {city}, {state}")
            return None

        match = address_matches[0]
        coordinates = match.get("coordinates", {})
        geographies = match.get("geographies", {})

        # Extract congressional district
        congressional_districts = geographies.get("Congressional Districts", [])
        district = None
        if congressional_districts:
            cd = congressional_districts[0]
            district_code = cd.get("CD118", cd.get("CD119", cd.get("CDFP", "")))
            if district_code and district_code.isdigit():
                district = int(district_code)
                # District 0 or 98 means at-large (single representative)
                if district in (0, 98):
                    district = 0  # Normalize to 0 for at-large

        # Extract state info
        states = geographies.get("States", [])
        state_name = states[0].get("NAME", state) if states else state

        return DistrictResult(
            state=state.upper(),
            state_name=state_name,
            district=district,
            formatted_address=match.get("matchedAddress"),
            lat=coordinates.get("y"),
            lng=coordinates.get("x"),
        )

    except httpx.HTTPError as e:
        logger.error(f"HTTP error finding district: {e}")
        return None
    except Exception as e:
        logger.error(f"Error finding district: {e}")
        return None


async def find_district_by_zip(zip_code: str) -> list[DistrictResult]:
    """
    Find congressional district(s) from a ZIP code.

    Note: A ZIP code may span multiple districts, so this returns a list.

    Args:
        zip_code: 5-digit ZIP code

    Returns:
        List of DistrictResult objects
    """
    # ZIP codes can span multiple districts, so we use a different approach
    # For simplicity, we geocode to the ZIP centroid and return single result
    params = {
        "address": zip_code,
        "benchmark": "Public_AR_Current",
        "vintage": "Current_Current",
        "layers": "54",
        "format": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        result = data.get("result", {})
        address_matches = result.get("addressMatches", [])

        results = []
        for match in address_matches[:3]:  # Limit to top 3 matches
            geographies = match.get("geographies", {})
            coordinates = match.get("coordinates", {})

            congressional_districts = geographies.get("Congressional Districts", [])
            states = geographies.get("States", [])

            for cd in congressional_districts:
                district_code = cd.get("CD118", cd.get("CD119", cd.get("CDFP", "")))
                district = None
                if district_code and district_code.isdigit():
                    district = int(district_code)
                    if district in (0, 98):
                        district = 0

                state_abbr = cd.get("STATE", "")
                state_name = states[0].get("NAME", "") if states else ""

                # Convert state FIPS to abbreviation
                state_abbr = _fips_to_state(state_abbr) or state_abbr

                results.append(
                    DistrictResult(
                        state=state_abbr,
                        state_name=state_name,
                        district=district,
                        formatted_address=match.get("matchedAddress"),
                        lat=coordinates.get("y"),
                        lng=coordinates.get("x"),
                    )
                )

        return results

    except Exception as e:
        logger.error(f"Error finding district by ZIP: {e}")
        return []


def _fips_to_state(fips: str) -> str | None:
    """Convert FIPS state code to state abbreviation."""
    fips_map = {
        "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
        "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
        "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
        "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
        "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
        "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
        "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
        "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
        "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
        "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
        "56": "WY", "72": "PR",
    }
    return fips_map.get(fips)
