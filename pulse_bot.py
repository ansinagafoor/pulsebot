"""
Pulse Bot — Daily weather + motivation snapshot.

Usage:
    python pulse_bot.py [CITY]

If CITY is omitted the bot uses the value of the PULSE_CITY environment
variable, falling back to "London".
"""

import os
import sys
import json
import datetime
import textwrap
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_CITY = os.getenv("PULSE_CITY", "London")
WTTR_URL     = "https://wttr.in/{city}?format=j1"
ZENQUOTES_URL = "https://zenquotes.io/api/random"
OUTPUT_FILE  = "summary.txt"

BANNER = "=" * 60


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_json(url: str, label: str) -> dict | list | None:
    """Fetch *url* and return parsed JSON, or None on error."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PulseBot/1.0 (+https://github.com/your-org/pulse-bot)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
        return json.loads(raw)
    except urllib.error.HTTPError as exc:
        print(f"[WARN] {label}: HTTP {exc.code} — {exc.reason}")
    except urllib.error.URLError as exc:
        print(f"[WARN] {label}: network error — {exc.reason}")
    except json.JSONDecodeError as exc:
        print(f"[WARN] {label}: JSON parse error — {exc}")
    return None


def get_weather(city: str) -> dict:
    """Return a tidy weather dict for *city* via wttr.in."""
    data = fetch_json(WTTR_URL.format(city=urllib.parse.quote(city)), "weather")
    if data is None:
        return {"city": city, "error": "Could not fetch weather data."}

    try:
        current   = data["current_condition"][0]
        area      = data["nearest_area"][0]
        area_name = area["areaName"][0]["value"]
        country   = area["country"][0]["value"]

        return {
            "city"        : f"{area_name}, {country}",
            "temp_c"      : current["temp_C"],
            "temp_f"      : current["temp_F"],
            "feels_like_c": current["FeelsLikeC"],
            "feels_like_f": current["FeelsLikeF"],
            "humidity"    : current["humidity"],
            "description" : current["weatherDesc"][0]["value"],
            "wind_kmph"   : current["windspeedKmph"],
            "wind_dir"    : current["winddir16Point"],
            "visibility"  : current["visibility"],
            "uv_index"    : current.get("uvIndex", "N/A"),
        }
    except (KeyError, IndexError) as exc:
        return {"city": city, "error": f"Unexpected data shape: {exc}"}


def get_quote() -> dict:
    """Return a motivational quote dict from ZenQuotes."""
    data = fetch_json(ZENQUOTES_URL, "quote")
    if data and isinstance(data, list) and data:
        item = data[0]
        return {"quote": item.get("q", ""), "author": item.get("a", "Unknown")}
    return {"quote": "Keep going — every step counts.", "author": "Pulse Bot"}


def build_summary(city: str) -> str:
    """Compose the full summary string."""
    now     = datetime.datetime.now().strftime("%A, %d %B %Y  %H:%M")
    weather = get_weather(city)
    quote   = get_quote()

    lines = [
        BANNER,
        "  ⚡  PULSE BOT — DAILY SNAPSHOT",
        BANNER,
        f"  Generated : {now}",
        "",
    ]

    # --- Weather block ---
    lines.append("  🌤  WEATHER")
    lines.append("  " + "-" * 56)

    if "error" in weather:
        lines.append(f"  ⚠  {weather['error']}")
    else:
        lines += [
            f"  Location    : {weather['city']}",
            f"  Condition   : {weather['description']}",
            f"  Temperature : {weather['temp_c']}°C  /  {weather['temp_f']}°F",
            f"  Feels Like  : {weather['feels_like_c']}°C  /  {weather['feels_like_f']}°F",
            f"  Humidity    : {weather['humidity']}%",
            f"  Wind        : {weather['wind_kmph']} km/h {weather['wind_dir']}",
            f"  Visibility  : {weather['visibility']} km",
            f"  UV Index    : {weather['uv_index']}",
        ]

    lines.append("")

    # --- Quote block ---
    lines.append("  💬  MOTIVATION")
    lines.append("  " + "-" * 56)

    wrapped = textwrap.wrap(quote["quote"], width=54)
    for i, segment in enumerate(wrapped):
        prefix = '  \u201c' if i == 0 else "   "
        lines.append(prefix + segment)
    lines[-1] += '\u201d'
    lines.append(f"      \u2014 {quote['author']}")
    lines.append("")

    lines.append(BANNER)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import urllib.parse  # noqa: PLC0415 — imported late so patch works in tests

    city    = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CITY
    summary = build_summary(city)

    print(summary)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        fh.write(summary)

    print(f"[INFO] Summary saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    import urllib.parse  # noqa: F401
    main()
