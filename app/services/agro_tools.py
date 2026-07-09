"""
AgroSight – Agent Tools
========================
Three LangGraph / LangChain tool-compatible callables:
  1. get_weather_advisory  – OpenWeatherMap current conditions + agro advisory
  2. get_mandi_price       – data.gov.in mandi price for commodity + market
  3. fertiliser_calculator – dose calculation from nutrient requirements

Each function is a plain Python async function that the LangGraph ReAct agent
calls when it decides tool use is needed.
"""

from __future__ import annotations

import asyncio
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.config import get_settings
from app.utils.logger import logger

settings = get_settings()

# ---------------------------------------------------------------------------
# Tool 1 – Weather advisory
# ---------------------------------------------------------------------------


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def get_weather_advisory(location: str) -> dict[str, Any]:
    """
    Fetch current weather for *location* (city name or lat,lon) from OpenWeatherMap
    and generate a short agronomy advisory based on conditions.

    Returns real-time weather data or error if source is unavailable.
    """
    if not settings.openweather_api_key:
        error_msg = (
            "OpenWeatherMap API key not configured. "
            "Cannot fetch real-time weather data. Please contact administrator."
        )
        logger.error(error_msg)
        return {
            "error": error_msg,
            "location": location,
            "status": "unavailable",
        }

    url = f"{settings.openweather_base_url}/weather"
    params = {
        "appid": settings.openweather_api_key,
        "units": "metric",
        "lang": "en",
    }

    # Support both city names and latitude,longitude strings.
    if isinstance(location, str) and "," in location:
        coords = [part.strip() for part in location.split(",", 1)]
        if len(coords) == 2 and all(coords):
            params["lat"], params["lon"] = coords
        else:
            params["q"] = location
    else:
        params["q"] = location

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        error_msg = f"OpenWeatherMap API error (HTTP {exc.response.status_code}): {exc.response.text}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "location": location,
            "status": "api_error",
        }
    except Exception as exc:
        error_msg = f"Failed to fetch weather for {location}: {exc}"
        logger.error(error_msg)
        return {
            "error": error_msg,
            "location": location,
            "status": "unavailable",
        }

    temp_c = data["main"]["temp"]
    humidity = data["main"]["humidity"]
    wind_mps = data["wind"]["speed"]
    wind_kmh = round(wind_mps * 3.6, 1)
    condition = data["weather"][0]["description"]
    rain_1h = data.get("rain", {}).get("1h", 0)
    feels_like = data["main"].get("feels_like", temp_c)

    advisory = _generate_advisory(temp_c, humidity, wind_kmh, condition, rain_1h)

    # Convert OpenWeatherMap Unix timestamp → IST human-readable string
    dt_unix = data.get("dt")
    if dt_unix:
        ist = datetime.fromtimestamp(dt_unix, tz=timezone(timedelta(hours=5, minutes=30)))
        observed_at = ist.strftime("%d %B %Y, %I:%M %p IST")
    else:
        observed_at = datetime.now(tz=timezone(timedelta(hours=5, minutes=30))).strftime("%d %B %Y, %I:%M %p IST")

    return {
        "location": data.get("name", location),
        "observed_at": observed_at,
        "data_freshness": "Real-time data from OpenWeatherMap. This is current weather, NOT historical.",
        "temperature_c": temp_c,
        "feels_like_c": round(feels_like, 1),
        "humidity_pct": humidity,
        "wind_kmh": wind_kmh,
        "condition": condition,
        "rain_last_hour_mm": rain_1h,
        "advisory": advisory,
        "source": "OpenWeatherMap (Real-time)",
    }


def _generate_advisory(
    temp_c: float,
    humidity: int,
    wind_kmh: float,
    condition: str,
    rain_mm: float,
) -> str:
    """Rule-based agronomy advisory from weather parameters."""
    tips: list[str] = []

    if rain_mm > 10:
        tips.append("Heavy rainfall detected — avoid irrigation and field operations today.")
    elif rain_mm > 2:
        tips.append("Light rain recorded — irrigation likely not required for the next 24h.")
    elif humidity < 40 and temp_c > 35:
        tips.append("Hot and dry conditions — irrigate crops early morning or evening.")

    if wind_kmh > 40:
        tips.append("High winds — postpone pesticide / fertiliser spraying to avoid drift.")
    elif wind_kmh > 20:
        tips.append("Moderate winds — use directed nozzles if spraying is necessary.")

    if temp_c > 40:
        tips.append("Extreme heat — protect nurseries and seedlings with shade netting.")
    elif temp_c < 5:
        tips.append("Near-frost temperatures — protect sensitive crops and avoid planting.")

    if humidity > 85 and temp_c > 25:
        tips.append("High humidity — monitor for fungal diseases (blast, blight). Consider preventive fungicide.")

    if not tips:
        tips.append("Conditions appear normal. Continue regular field monitoring.")

    return " ".join(tips)


# ---------------------------------------------------------------------------
# Tool 2 – Mandi price lookup with CSV fallback
# ---------------------------------------------------------------------------

async def _fetch_from_csv_fallback(
    commodity: str, market: str, state: str
) -> dict[str, Any] | None:
    """
    Fallback to local CSV data when APIs are unavailable.
    Searches mandi_data/mandi_prices_YYYY-MM-DD.csv for matching records.
    Returns the most recent matching record or None if not found.
    """
    try:
        # Find the most recent CSV file in mandi_data/
        mandi_dir = Path("./mandi_data")
        if not mandi_dir.exists():
            logger.debug("mandi_data directory not found")
            return None

        csv_files = sorted(mandi_dir.glob("mandi_prices_*.csv"), reverse=True)
        if not csv_files:
            logger.debug("No mandi price CSV files found")
            return None

        csv_path = csv_files[0]
        logger.debug(f"Using CSV fallback: {csv_path.name}")

        commodity_lower = commodity.lower().strip()
        market_lower = market.lower().strip() if market else ""
        state_lower = state.lower().strip() if state else "gujaratgujaratgujarat"

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            matching_records = []

            for row in reader:
                # Case-insensitive matching
                row_commodity = row.get("commodity", "").lower().strip()
                row_market = row.get("market", "").lower().strip()
                row_state = row.get("state", "").lower().strip()

                # Match commodity (required)
                if commodity_lower not in row_commodity and row_commodity not in commodity_lower:
                    continue

                # Match state (required)
                if state_lower != row_state and state_lower not in row_state and row_state not in state_lower:
                    continue

                # Match market (optional, but prefer exact match)
                if market_lower:
                    if market_lower not in row_market and row_market not in market_lower:
                        continue

                matching_records.append(row)

        if not matching_records:
            logger.debug(f"No CSV records found for {commodity}/{market or 'any'}/{state}")
            return None

        # Return the first (most recent, since CSV is sorted by date)
        latest = matching_records[0]
        arrival = latest.get("arrival_date", "")
        csv_date = csv_path.name.replace("mandi_prices_", "").replace(".csv", "")

        return {
            "commodity": latest.get("commodity", commodity),
            "market": latest.get("market", market),
            "state": latest.get("state", state),
            "variety": latest.get("variety"),
            "grade": latest.get("grade"),
            "modal_price_inr": float(latest["modal_price"]) if latest.get("modal_price") else None,
            "min_price_inr": float(latest["min_price"]) if latest.get("min_price") else None,
            "max_price_inr": float(latest["max_price"]) if latest.get("max_price") else None,
            "arrival_date": arrival,
            "data_lag_note": (
                f"⚠️ CACHED DATA (APIs unavailable): Price data is from {arrival}. "
                f"CSV data ingested on {csv_date}. Real-time sources (data.gov.in, agmarknet) "
                f"are currently unreachable. This is historical data, not live market price."
            ),
            "source": "Local CSV fallback (APIs unavailable)",
            "is_fallback": True,
        }

    except Exception as exc:
        logger.debug(f"CSV fallback error: {exc}")
        return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def get_mandi_price(commodity: str, market: str = "", state: str = "Gujarat") -> dict[str, Any]:
    """
    Fetch real-time modal price for *commodity* at *market* from multiple sources.
    
    Primary: data.gov.in Agmarknet API
    Secondary: Agmarknet direct API
    Fallback: Local CSV cache when APIs unavailable
    
    Returns latest price data with source information.
    Falls back to cached CSV data if both live APIs fail.
    """
    commodity_normalized = commodity.lower().strip()
    market_normalized = market.lower().strip() if market else ""
    state_normalized = state.lower().strip() if state else "Gujarat"

    logger.debug(f"Fetching mandi price for {commodity_normalized} in {market_normalized or 'any market'}, {state_normalized}")

    # Try primary source: data.gov.in
    try:
        data_gov_result = await _fetch_from_data_gov_in(
            commodity_normalized, market_normalized, state_normalized
        )
        if data_gov_result:
            return data_gov_result
    except asyncio.TimeoutError:
        logger.warning(f"data.gov.in request timed out, trying secondary source")
    except Exception as exc:
        logger.warning(f"data.gov.in error: {exc}, trying secondary source")

    # Try secondary source: Agmarknet direct API
    try:
        agmarknet_result = await _fetch_from_agmarknet(
            commodity_normalized, market_normalized, state_normalized
        )
        if agmarknet_result:
            return agmarknet_result
    except asyncio.TimeoutError:
        logger.warning(f"Agmarknet request timed out, falling back to CSV")
    except Exception as exc:
        logger.warning(f"Agmarknet error: {exc}, falling back to CSV")

    # Try CSV fallback when live APIs fail
    logger.info("Live APIs unavailable, attempting CSV fallback...")
    try:
        csv_result = await _fetch_from_csv_fallback(
            commodity_normalized, market_normalized, state_normalized
        )
        if csv_result:
            logger.info(f"CSV fallback succeeded for {commodity}/{market or 'any'}/{state}")
            return csv_result
    except Exception as exc:
        logger.warning(f"CSV fallback error: {exc}")

    # If all sources fail (including CSV), return error
    error_msg = (
        f"Unable to fetch price for {commodity} in {market or 'any market'}, {state}. "
        f"All sources unavailable (live APIs down, no cached data found). Please try again later."
    )
    logger.error(error_msg)
    return {
        "error": error_msg,
        "commodity": commodity,
        "market": market,
        "state": state,
        "status": "unavailable",
        "available_sources": ["data.gov.in (TIMEOUT)", "agmarknet.gov.in (TIMEOUT)", "local CSV (NOT FOUND)"],
    }



async def _fetch_from_data_gov_in(
    commodity: str, market: str, state: str
) -> dict[str, Any] | None:
    """
    Fetch price data from data.gov.in using BOTH Agmarknet-backed datasets.

    Resource 1 (9ef84268): Current Daily Price — filter keys: filters[state.keyword], filters[market], filters[commodity]
    Resource 2 (35985678): Variety-wise Daily Price — filter keys: filters[State], filters[District], filters[Commodity]

    Fetches 50 records and sorts CLIENT-SIDE by arrival_date DESC — the API
    returns records in arbitrary order, so requesting only 5 can give week-old
    data even when newer records exist in the full dataset.
    Returns None if both are unavailable or return no results.
    """

    def _parse_ddmmyyyy(raw: str) -> tuple:
        """Parse DD/MM/YYYY into (YYYY, MM, DD) for descending sort."""
        try:
            d, m, y = raw.split("/")
            return (int(y), int(m), int(d))
        except Exception:
            return (0, 0, 0)

    api_key = settings.data_gov_api_key_1
    if not api_key:
        logger.debug("data.gov.in API key not configured, skipping this source")
        return None

    base = settings.data_gov_base_url  # https://api.data.gov.in

    # ── Resource 1: Current Daily Price (9ef84268) ──────────────────────────
    # Official filter keys: filters[state.keyword], filters[district], filters[market], filters[commodity]
    r1_id = settings.data_gov_mandi_resource_id  # 9ef84268-d588-465a-a308-a864a43d0070
    r1_params: dict[str, Any] = {
        "api-key": api_key,
        "format": "json",
        "filters[commodity]": commodity.title(),
        "limit": 50,  # Fetch enough records to find the most recent after client-side sort
    }
    if market:
        r1_params["filters[market]"] = market.title()
    if state:
        r1_params["filters[state.keyword]"] = state.title()

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
            resp = await client.get(f"{base}/resource/{r1_id}", params=r1_params)
            resp.raise_for_status()
            data = resp.json()
        records = data.get("records", [])
        if records:
            # Sort descending by arrival_date so we always get the most recent record
            records.sort(key=lambda r: _parse_ddmmyyyy(r.get("arrival_date", "")), reverse=True)
            latest = records[0]
            arrival = latest.get("arrival_date", "")
            logger.info(f"data.gov.in R1 → {commodity}@{market or 'any'},{state} | latest: {arrival}")
            return {
                "commodity": latest.get("commodity", commodity.title()),
                "market": latest.get("market", market),
                "state": latest.get("state", state),
                "variety": latest.get("variety"),
                "grade": latest.get("grade"),
                "modal_price_inr": float(latest["modal_price"]) if latest.get("modal_price") else None,
                "min_price_inr": float(latest["min_price"]) if latest.get("min_price") else None,
                "max_price_inr": float(latest["max_price"]) if latest.get("max_price") else None,
                "arrival_date": arrival,
                "data_lag_note": (
                    f"Most recent government-reported data is from {arrival}. "
                    "APMC mandi reporting has a typical 5–8 day lag. "
                    "Always show this date explicitly — never say 'today'."
                ),
                "source": "data.gov.in – Current Daily Mandi Price (AGMARKNET)",
            }
        logger.info(f"Resource 1 returned no records for {commodity}/{state}, trying resource 2")
    except asyncio.TimeoutError:
        logger.debug(f"data.gov.in resource 1 timeout (>{settings.request_timeout}s) — trying resource 2")
    except httpx.HTTPStatusError as exc:
        logger.debug(f"data.gov.in resource 1 HTTP error {exc.response.status_code} — trying resource 2")
    except Exception as exc:
        logger.debug(f"data.gov.in resource 1 error: {exc} — trying resource 2")

    # ── Resource 2: Variety-wise Daily Price (35985678) ─────────────────────
    # Official filter keys: filters[State], filters[District], filters[Commodity], filters[Arrival_Date]
    r2_id = settings.data_gov_variety_resource_id  # 35985678-0d79-46b4-9ed6-6f13308a1d24
    r2_params: dict[str, Any] = {
        "api-key": api_key,
        "format": "json",
        "filters[Commodity]": commodity.title(),
        "limit": 50,  # Fetch enough records to find the most recent after client-side sort
    }
    if state:
        r2_params["filters[State]"] = state.title()

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
            resp = await client.get(f"{base}/resource/{r2_id}", params=r2_params)
            resp.raise_for_status()
            data = resp.json()
        records = data.get("records", [])
        if records:
            records.sort(
                key=lambda r: _parse_ddmmyyyy(r.get("Arrival_Date", r.get("arrival_date", ""))),
                reverse=True,
            )
            latest = records[0]
            arrival = latest.get("Arrival_Date", latest.get("arrival_date", ""))
            logger.info(f"data.gov.in R2 → {commodity}@{state} | latest: {arrival}")
            return {
                "commodity": latest.get("Commodity", latest.get("commodity", commodity.title())),
                "market": latest.get("Market", latest.get("market", market)),
                "state": latest.get("State", latest.get("state", state)),
                "modal_price_inr": float(latest["Modal_Price"]) if latest.get("Modal_Price") else (
                    float(latest["modal_price"]) if latest.get("modal_price") else None
                ),
                "min_price_inr": float(latest["Min_Price"]) if latest.get("Min_Price") else (
                    float(latest["min_price"]) if latest.get("min_price") else None
                ),
                "max_price_inr": float(latest["Max_Price"]) if latest.get("Max_Price") else (
                    float(latest["max_price"]) if latest.get("max_price") else None
                ),
                "arrival_date": arrival,
                "data_lag_note": (
                    f"Most recent government-reported data is from {arrival}. "
                    "APMC mandi reporting has a typical 5–8 day lag. "
                    "Always show this date explicitly — never say 'today'."
                ),
                "source": "data.gov.in – Variety-wise Daily Mandi Price (AGMARKNET)",
            }
        logger.info(f"Resource 2 also returned no records for {commodity}/{state}")
    except asyncio.TimeoutError:
        logger.debug(f"data.gov.in resource 2 timeout (>{settings.request_timeout}s)")
    except httpx.HTTPStatusError as exc:
        logger.debug(f"data.gov.in resource 2 HTTP error {exc.response.status_code}")
    except Exception as exc:
        logger.debug(f"data.gov.in resource 2 error: {exc}")

    return None


async def _fetch_from_agmarknet(
    commodity: str, market: str, state: str
) -> dict[str, Any] | None:
    """
    Fetch price data directly from Agmarknet API.
    Returns None if API is unavailable or returns no results.
    """
    api_key = settings.agmarknet_api_key
    base_url = settings.agmarknet_base_url

    if not api_key:
        logger.debug("Agmarknet API key not configured, skipping this source")
        return None

    # Agmarknet API endpoint for commodity prices
    url = f"{base_url}/commodity-price"
    params: dict[str, Any] = {
        "api_key": api_key,
        "commodity": commodity.title(),
        "limit": 5,
    }
    if market:
        params["market"] = market.title()
    if state:
        params["state"] = state.title()

    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout, follow_redirects=True) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        records = data.get("records", data.get("data", []))
        if not records:
            logger.info(f"No records found for {commodity} in {market or 'any'} market on agmarknet.gov.in")
            return None

        latest = records[0]
        return {
            "commodity": latest.get("commodity", commodity),
            "market": latest.get("market", market),
            "state": latest.get("state", state),
            "modal_price_inr": float(latest.get("modal_price", latest.get("price"))) 
                if (latest.get("modal_price") or latest.get("price")) else None,
            "min_price_inr": float(latest.get("min_price")) if latest.get("min_price") else None,
            "max_price_inr": float(latest.get("max_price")) if latest.get("max_price") else None,
            "arrival_date": latest.get("arrival_date", latest.get("date")),
            "source": "agmarknet.gov.in (Direct)",
            "timestamp": latest.get("timestamp"),
        }

    except asyncio.TimeoutError:
        logger.debug(f"Agmarknet API timeout (>{settings.request_timeout}s) — all sources exhausted")
        return None
    except httpx.HTTPStatusError as exc:
        logger.debug(f"Agmarknet API HTTP error {exc.response.status_code} — all sources exhausted")
        return None
    except Exception as exc:
        logger.debug(f"Agmarknet API error: {exc} — all sources exhausted")
        return None



# ---------------------------------------------------------------------------
# Tool 3 – Fertiliser dose calculator
# ---------------------------------------------------------------------------

# Nutrient content of common fertilisers (% N, P2O5, K2O)
_FERTILISER_COMPOSITION: dict[str, dict[str, float]] = {
    "urea": {"N": 46.0, "P": 0.0, "K": 0.0},
    "dap": {"N": 18.0, "P": 46.0, "K": 0.0},
    "mop": {"N": 0.0, "P": 0.0, "K": 60.0},
    "ssp": {"N": 0.0, "P": 16.0, "K": 0.0},
    "10:26:26": {"N": 10.0, "P": 26.0, "K": 26.0},
    "12:32:16": {"N": 12.0, "P": 32.0, "K": 16.0},
    "npk 20:20:0": {"N": 20.0, "P": 20.0, "K": 0.0},
}

# Per-crop nutrient requirements (kg/ha) — simplified representative values
_CROP_NUTRIENT_REQ: dict[str, dict[str, float]] = {
    "wheat": {"N": 120, "P": 60, "K": 40},
    "rice": {"N": 120, "P": 60, "K": 60},
    "cotton": {"N": 150, "P": 60, "K": 60},
    "maize": {"N": 150, "P": 75, "K": 50},
    "soybean": {"N": 20, "P": 80, "K": 40},
    "sugarcane": {"N": 250, "P": 100, "K": 120},
    "potato": {"N": 150, "P": 100, "K": 150},
    "onion": {"N": 100, "P": 60, "K": 60},
    "tomato": {"N": 120, "P": 80, "K": 60},
    "groundnut": {"N": 25, "P": 50, "K": 50},
    "mango": {"N": 100, "P": 50, "K": 100},
}


async def fertiliser_calculator(
    crop: str,
    area_acres: float,
    fertiliser: str = "urea",
    nutrient: str = "N",
) -> dict[str, Any]:
    """
    Calculate fertiliser quantity needed for *crop* on *area_acres*.

    Args:
        crop: crop name (e.g. 'wheat')
        area_acres: field area in acres
        fertiliser: fertiliser product (e.g. 'urea', 'dap')
        nutrient: which nutrient to calculate for ('N', 'P', or 'K')

    Returns:
        dict with dose_kg, bags_50kg, cost_estimate_inr, notes
    """
    crop_key = crop.lower().strip()
    fert_key = fertiliser.lower().strip()
    nut_key = nutrient.upper()

    crop_req = _CROP_NUTRIENT_REQ.get(crop_key)
    fert_comp = _FERTILISER_COMPOSITION.get(fert_key)

    if crop_req is None:
        return {
            "error": f"Crop '{crop}' not in database. Please consult local ICAR advisory.",
            "available_crops": list(_CROP_NUTRIENT_REQ.keys()),
        }

    if fert_comp is None:
        return {
            "error": f"Fertiliser '{fertiliser}' not in database.",
            "available_fertilisers": list(_FERTILISER_COMPOSITION.keys()),
        }

    if nut_key not in ("N", "P", "K"):
        return {"error": "Nutrient must be N, P, or K."}

    nutrient_content_pct = fert_comp.get(nut_key, 0)
    if nutrient_content_pct == 0:
        return {
            "error": f"{fertiliser.upper()} contains no {nut_key}. Choose appropriate fertiliser.",
        }

    area_ha = area_acres * 0.4047
    required_nutrient_kg = crop_req[nut_key] * area_ha
    fertiliser_dose_kg = required_nutrient_kg / (nutrient_content_pct / 100)
    bags_50kg = round(fertiliser_dose_kg / 50, 1)

    # Rough price estimates (INR/50kg bag, 2024 approx)
    bag_prices = {"urea": 266, "dap": 1350, "mop": 900, "ssp": 450}
    bag_price = bag_prices.get(fert_key, 1000)
    cost_inr = round(bags_50kg * bag_price)

    return {
        "crop": crop,
        "area_acres": area_acres,
        "area_ha": round(area_ha, 2),
        "nutrient": nut_key,
        "nutrient_required_kg": round(required_nutrient_kg, 1),
        "fertiliser": fertiliser.upper(),
        "fertiliser_dose_kg": round(fertiliser_dose_kg, 1),
        "bags_50kg": bags_50kg,
        "cost_estimate_inr": cost_inr,
        "notes": (
            f"Based on recommended {nut_key} dose of {crop_req[nut_key]} kg/ha for {crop}. "
            "Actual requirement may vary by soil test results. "
            "Apply in split doses as per crop growth stage."
        ),
        "source": "AgroSight nutrient requirement database",
    }
