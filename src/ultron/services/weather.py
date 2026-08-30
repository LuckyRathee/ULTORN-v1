"""
Weather Service - Real weather API integration (WeatherAPI.com).

Simple, reliable API with free tier. Returns structured data.
"""

from dataclasses import dataclass
from typing import Optional, Literal
import httpx

from ..config import settings
from ..utils.errors import UltronError


@dataclass
class WeatherData:
    """Structured weather data."""
    location: str
    temperature: float
    condition: str
    humidity: int
    wind_kph: float
    feels_like: float
    last_updated: str


class WeatherError(UltronError):
    """Weather API error with typed error_type."""
    def __init__(self, message: str, error_type: Literal["timeout", "rate_limit", "server_error", "auth", "bad_params", "not_found", "unknown"]):
        self.error_type = error_type
        super().__init__(message)
    
    code = "WEATHER_ERROR"
    user_message = "I couldn't retrieve the weather information."


async def get_weather(
    location: str,
    units: Literal["metric", "imperial"] = "metric",
) -> dict:
    """
    Get current weather for a location.
    
    Args:
        location: City name, "lat,lon", or IP address
        units: "metric" (Celsius) or "imperial" (Fahrenheit)
        
    Returns:
        Dict with weather data matching WeatherData fields
        
    Raises:
        WeatherError: With typed error_type
    """
    if not settings.weather_api_key:
        raise WeatherError("Weather API key not configured", "auth")
    
    url = f"{settings.weather_api_base}/current.json"

    params = {
        "key": settings.weather_api_key,
        "q": location,
        "aqi": "no",
    }
    
    timeout = httpx.Timeout(10.0, connect=5.0)
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(url, params=params)
        except httpx.TimeoutException as e:
            raise WeatherError("Weather API timeout", "timeout") from e
        except httpx.RequestError as e:
            raise WeatherError(f"Weather API request failed: {e}", "server_error") from e
    
    if response.status_code == 400:
        # Check if it's an invalid location
        try:
            error_data = response.json()
            if "error" in error_data and error_data["error"].get("code") == 1006:
                raise WeatherError(f"Location not found: {location}", "not_found")
        except Exception:
            pass
        raise WeatherError(f"Weather API bad request: {response.text}", "bad_params")
    elif response.status_code == 401:
        raise WeatherError("Weather API authentication failed", "auth")
    elif response.status_code == 429:
        raise WeatherError("Weather API rate limit exceeded", "rate_limit")
    elif response.status_code >= 500:
        raise WeatherError(f"Weather API server error: {response.status_code}", "server_error")
    elif response.status_code != 200:
        raise WeatherError(f"Weather API error: {response.text}", "unknown")
    
    try:
        data = response.json()
    except Exception as e:
        raise WeatherError(f"Invalid JSON response: {e}", "server_error") from e
    
    # Extract relevant fields
    current = data.get("current", {})
    location_info = data.get("location", {})
    
    temp_key = "temp_c" if units == "metric" else "temp_f"
    feels_like_key = "feelslike_c" if units == "metric" else "feelslike_f"
    wind_key = "wind_kph" if units == "metric" else "wind_mph"
    
    return {
        "location": f"{location_info.get('name', '')}, {location_info.get('country', '')}".strip(", "),
        "temperature": current.get(temp_key),
        "condition": current.get("condition", {}).get("text", "unknown"),
        "humidity": current.get("humidity"),
        "wind_kph": current.get(wind_key),
        "feels_like": current.get(feels_like_key),
        "last_updated": current.get("last_updated"),
    }


def get_default_location() -> str:
    """Get the default location for weather queries."""
    return settings.default_city
